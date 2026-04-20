# Deploying the Vaughn RAG Backend to AWS App Runner

This guide walks through deploying the Dockerized FastAPI chatbot in `Backend/`
to **AWS App Runner**, a fully managed container service that handles load
balancing, TLS, and autoscaling for you.

The Dockerfile already:
- Exposes port `8000` and honors the `$PORT` env var that App Runner injects.
- Bakes `Pipeline/chroma_db` into the image (no volume mount needed).
- Ships a `/health` endpoint used for healthchecks.

Region used throughout this guide: **`us-east-1`**. Substitute your own.

---

## 1. Prerequisites

### 1.1 AWS account
1. Create an account at <https://aws.amazon.com> if you don't already have one.
2. Enable MFA on the root user, then create an **IAM user** for daily use —
   never deploy from the root account.
3. In **IAM → Users → your user → Security credentials**, create an **Access
   key** of type *Command Line Interface (CLI)*. Save the access key ID and
   secret somewhere safe (a password manager).

### 1.2 Install the AWS CLI
- **Windows**: download the MSI from
  <https://awscli.amazonaws.com/AWSCLIV2.msi> and run it.
- Verify:
  ```bash
  aws --version
  # aws-cli/2.x.x Python/3.x.x Windows/10 ...
  ```

### 1.3 Configure credentials
```bash
aws configure
# AWS Access Key ID:     <paste>
# AWS Secret Access Key: <paste>
# Default region name:   us-east-1
# Default output format: json
```

Sanity check:
```bash
aws sts get-caller-identity
```
You should see your account ID and IAM user ARN.

### 1.4 IAM permissions you need
For an end-to-end deploy your IAM user needs (attach via **IAM → Users → Add
permissions → Attach policies directly**):

| Policy | Why |
|---|---|
| `AmazonEC2ContainerRegistryFullAccess` | Create repo + push image to ECR |
| `AWSAppRunnerFullAccess` | Create/update App Runner services |
| `IAMFullAccess` *(or scoped)* | App Runner needs an **access role** that lets it pull from ECR; creating that role requires IAM perms |
| `CloudWatchLogsReadOnlyAccess` | Read service logs |

For production, scope these down. For a first deploy these are fine.

You also need **Docker Desktop** running locally to build and push the image.

---

## 2. Push the Docker image to Amazon ECR

ECR (Elastic Container Registry) is AWS's private Docker registry. App Runner
will pull from here.

Set a few shell variables once so the rest of the commands are copy-pasteable:

```bash
export AWS_REGION=us-east-1
export AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
export ECR_REPO=vaughn-rag-backend
export IMAGE_TAG=v1
export ECR_URI=${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com/${ECR_REPO}
```

> On Windows `cmd.exe`, use `set VAR=value` instead of `export`. PowerShell
> uses `$env:VAR = "value"`. Git Bash supports `export` as shown.

### 2.1 Create the ECR repository
```bash
aws ecr create-repository \
  --repository-name "$ECR_REPO" \
  --image-scanning-configuration scanOnPush=true \
  --region "$AWS_REGION"
```

You should see JSON containing `"repositoryUri": "...amazonaws.com/vaughn-rag-backend"`.

### 2.2 Authenticate Docker to ECR
```bash
aws ecr get-login-password --region "$AWS_REGION" \
  | docker login --username AWS --password-stdin "${AWS_ACCOUNT_ID}.dkr.ecr.${AWS_REGION}.amazonaws.com"
```
Expected output: `Login Succeeded`.

### 2.3 Build and tag the image
The Dockerfile expects the build context to be the **repo root**, not
`Backend/`, because it copies both `Backend/app` and `Pipeline/chroma_db`.

From the repo root (`RAG_Vaughn/`):
```bash
docker build \
  -f Backend/Dockerfile \
  -t ${ECR_REPO}:${IMAGE_TAG} \
  .

docker tag ${ECR_REPO}:${IMAGE_TAG} ${ECR_URI}:${IMAGE_TAG}
```

Quick local smoke test before pushing (optional but recommended):
```bash
docker run --rm -p 8000:8000 \
  -e ANTHROPIC_API_KEY=sk-ant-... \
  -e OPENAI_API_KEY=sk-... \
  ${ECR_REPO}:${IMAGE_TAG}
# Visit http://localhost:8000/health
```

### 2.4 Push to ECR
```bash
docker push ${ECR_URI}:${IMAGE_TAG}
```
First push uploads all layers; subsequent pushes only upload changed layers.

Verify in the console: **ECR → Repositories → vaughn-rag-backend** should now
list a `v1` image.

---

## 2.5 Store secrets in AWS Secrets Manager (recommended)

Plain `RuntimeEnvironmentVariables` work, but they have downsides:
- API keys are visible in plaintext to anyone with read access to the App
  Runner console or `describe-service` IAM permission.
- Rotating a key requires editing the service config and triggering a redeploy.
- There's no audit trail for who pulled the key value.
- The keys end up in your shell history and your `apprunner-service.json` on
  disk.

Secrets Manager fixes all four: keys are stored encrypted, App Runner injects
them as env vars at container start, you can rotate them in place, and every
`GetSecretValue` call is logged in CloudTrail.

> If you're skipping this section for a quick first deploy, that's fine — you
> can always migrate to Secrets Manager later by editing the service.

### 2.5.1 Create the two secrets
Reusing the shell variables from §2:

```bash
aws secretsmanager create-secret \
  --name vaughn-rag/anthropic-key \
  --description "Anthropic API key for Vaughn RAG backend" \
  --secret-string "sk-ant-..." \
  --region "$AWS_REGION"

aws secretsmanager create-secret \
  --name vaughn-rag/openai-key \
  --description "OpenAI API key for Vaughn RAG backend" \
  --secret-string "sk-..." \
  --region "$AWS_REGION"
```

> **Don't paste the key on the command line in shared terminals** — it ends up
> in shell history. Safer alternative: `--secret-string file://anthropic.txt`
> and delete the file afterwards.

To rotate a key later (no redeploy needed; App Runner re-fetches on the next
instance start):
```bash
aws secretsmanager put-secret-value \
  --secret-id vaughn-rag/anthropic-key \
  --secret-string "sk-ant-NEWVALUE..."
```

### 2.5.2 Capture the secret ARNs
App Runner references secrets **by full ARN**, not by name. Stash them in
shell variables:

```bash
export ANTHROPIC_SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id vaughn-rag/anthropic-key \
  --query ARN --output text)

export OPENAI_SECRET_ARN=$(aws secretsmanager describe-secret \
  --secret-id vaughn-rag/openai-key \
  --query ARN --output text)

echo "$ANTHROPIC_SECRET_ARN"
echo "$OPENAI_SECRET_ARN"
```

ARNs look like
`arn:aws:secretsmanager:us-east-1:123456789012:secret:vaughn-rag/anthropic-key-AbCdEf`.
The trailing 6-character suffix is required.

### 2.5.3 Create an App Runner *instance* role with read access
The **access role** from §3.1 is what App Runner uses to *pull the image*.
Reading secrets at runtime is a separate concern handled by the **instance
role**, which is the IAM identity your container code runs as.

Create it once:

```bash
cat > apprunner-tasks-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "tasks.apprunner.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name AppRunnerInstanceRole \
  --assume-role-policy-document file://apprunner-tasks-trust.json
```

Now grant it read-only access to **only** the two secrets we created (least
privilege — don't use `Resource: "*"`):

```bash
cat > apprunner-secrets-policy.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "secretsmanager:GetSecretValue",
      "secretsmanager:DescribeSecret"
    ],
    "Resource": [
      "${ANTHROPIC_SECRET_ARN}",
      "${OPENAI_SECRET_ARN}"
    ]
  }]
}
EOF

aws iam put-role-policy \
  --role-name AppRunnerInstanceRole \
  --policy-name VaughnRagSecretsRead \
  --policy-document file://apprunner-secrets-policy.json

export INSTANCE_ROLE_ARN=$(aws iam get-role \
  --role-name AppRunnerInstanceRole \
  --query Role.Arn --output text)
```

If your secrets are encrypted with a customer-managed KMS key (not the default
`aws/secretsmanager` key), also add `kms:Decrypt` on that key's ARN.

### 2.5.4 Reference the secrets from App Runner

**Console path** — when creating or editing the service:
1. **Configure service → Environment variables** section.
2. Click **Add environment variable** and switch the *Source* dropdown from
   **Plain text** to **Secrets Manager**.
3. *Name* = `ANTHROPIC_API_KEY`, *Value* = paste the full ARN from
   `$ANTHROPIC_SECRET_ARN`.
4. Repeat for `OPENAI_API_KEY` / `$OPENAI_SECRET_ARN`.
5. Under **Security → Instance role**, pick **AppRunnerInstanceRole**. This is
   the step people most often miss — without it, App Runner will fail to start
   the container with an `AccessDeniedException`.

**CLI / JSON path** — replace `RuntimeEnvironmentVariables` with
`RuntimeEnvironmentSecrets` in `apprunner-service.json`, and add an
`InstanceConfiguration.InstanceRoleArn`:

```json
"ImageConfiguration": {
  "Port": "8000",
  "RuntimeEnvironmentSecrets": {
    "ANTHROPIC_API_KEY": "arn:aws:secretsmanager:us-east-1:123456789012:secret:vaughn-rag/anthropic-key-AbCdEf",
    "OPENAI_API_KEY":    "arn:aws:secretsmanager:us-east-1:123456789012:secret:vaughn-rag/openai-key-GhIjKl"
  }
}
```
```json
"InstanceConfiguration": {
  "Cpu": "256",
  "Memory": "512",
  "InstanceRoleArn": "arn:aws:iam::123456789012:role/AppRunnerInstanceRole"
}
```

You can mix the two: keep non-sensitive config in `RuntimeEnvironmentVariables`
(e.g. `LOG_LEVEL=info`) and only the keys in `RuntimeEnvironmentSecrets`.

### 2.5.5 Verify it's working
After the next deploy, tail the application log group from §5.2:

```bash
aws logs tail /aws/apprunner/vaughn-rag-backend/<id>/application --since 10m
```

Healthy startup looks like normal uvicorn boot logs and a 200 on `/health`.
App Runner does **not** print "fetched secret X" — successful retrieval is
silent. If your code logs whether the keys are set (e.g. on startup), that's a
good early signal.

What failure looks like:

| Log message | Meaning | Fix |
|---|---|---|
| `ResourceNotFoundException: Secrets Manager can't find the specified secret` | ARN is wrong, or secret is in a different region | Re-run §2.5.2; confirm region matches the App Runner service |
| `AccessDeniedException ... is not authorized to perform: secretsmanager:GetSecretValue` | Instance role missing or policy doesn't list this secret's ARN | Re-check §2.5.3; confirm `InstanceRoleArn` is set on the service |
| Service stuck in `CREATE_FAILED` with `Failed to retrieve secrets` event | Same as above, surfaced at the platform level | Look at the **service** log group (not application) for the exact reason |
| `KMS AccessDeniedException` | Secret uses a CMK and the role lacks `kms:Decrypt` | Add `kms:Decrypt` on that key ARN to `VaughnRagSecretsRead` |
| App boots but `ANTHROPIC_API_KEY` is empty inside the container | Used `RuntimeEnvironmentVariables` *and* `RuntimeEnvironmentSecrets` with the same key — the plain one wins | Remove the duplicate from `RuntimeEnvironmentVariables` |

### 2.5.6 Cost
Secrets Manager bills **$0.40 per secret per month** plus **$0.05 per 10,000
API calls**. Two secrets ≈ **$0.80/month**, and the API-call charge is
effectively zero since App Runner only fetches on instance start.

This is the single biggest "is it worth it?" question for hobby deploys —
$0.80/month buys you encryption at rest, rotation without redeploys, audit
logs in CloudTrail, and no plaintext keys in your service config. For anything
you'd be embarrassed to leak, it's worth it.

---

## 3. Deploy to AWS App Runner

App Runner can be created via console or CLI. The console is easier the first
time, the CLI is reproducible. Both are shown.

### 3.1 Create the access role (one-time)
App Runner needs an IAM role that grants it permission to pull from your
private ECR repo. Create it once and reuse it:

```bash
cat > apprunner-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "build.apprunner.amazonaws.com" },
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam create-role \
  --role-name AppRunnerECRAccessRole \
  --assume-role-policy-document file://apprunner-trust.json

aws iam attach-role-policy \
  --role-name AppRunnerECRAccessRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
```

Capture the role ARN:
```bash
export ACCESS_ROLE_ARN=$(aws iam get-role \
  --role-name AppRunnerECRAccessRole \
  --query Role.Arn --output text)
```

### 3.2 Create the App Runner service — Console walkthrough
1. Go to **AWS Console → App Runner → Create service**.
2. **Source**:
   - *Repository type*: **Container registry**
   - *Provider*: **Amazon ECR**
   - *Container image URI*: click **Browse** and pick
     `vaughn-rag-backend:v1`.
3. **Deployment settings**:
   - *Deployment trigger*: **Manual** (cheapest) or **Automatic** (redeploys
     when you push a new tag).
   - *ECR access role*: pick the existing **AppRunnerECRAccessRole**.
4. **Service settings**:
   - *Service name*: `vaughn-rag-backend`
   - *Virtual CPU & memory*: start with **0.25 vCPU / 0.5 GB**. Bump only if
     you OOM — chromadb embeddings can be hungry.
   - *Port*: **8000**
   - *Environment variables*: add your config here. For API keys, **use
     Secrets Manager** instead of plain text — follow §2.5 to create the
     secrets and instance role, then in this section click **Add environment
     variable**, switch *Source* to **Secrets Manager**, and paste the ARNs:
     - `ANTHROPIC_API_KEY` → `$ANTHROPIC_SECRET_ARN`
     - `OPENAI_API_KEY` → `$OPENAI_SECRET_ARN`
     Quick-and-dirty plain-text fallback (not recommended for real keys):
     `ANTHROPIC_API_KEY = sk-ant-...`, `OPENAI_API_KEY = sk-...`.
5. **Auto scaling**: click **Add new** and configure:
   - *Concurrency*: `100` (requests per instance before scaling out)
   - *Min size*: `1`
   - *Max size*: `2` for a hobby site, `5+` for production
6. **Health check**:
   - *Protocol*: **HTTP**
   - *Path*: `/health`
   - *Interval*: `10s`, *Timeout*: `5s`, *Healthy threshold*: `1`,
     *Unhealthy threshold*: `5`
7. **Security**: if you're using Secrets Manager (§2.5), set *Instance role*
   to **AppRunnerInstanceRole** — without it, the container will fail to start
   with `AccessDeniedException`. Otherwise, leave the default unless your app
   calls other AWS services (S3, DynamoDB…), in which case attach a least-priv
   role.
8. Click **Create & deploy**. First deploy takes ~5 minutes. When status flips
   to **Running**, you'll get a URL like
   `https://abcd1234.us-east-1.awsapprunner.com`.

### 3.3 Create the service via CLI (alternative)
Save this as `apprunner-service.json`. This version uses **Secrets Manager**
for API keys (§2.5) — swap `RuntimeEnvironmentSecrets` for
`RuntimeEnvironmentVariables` if you're going the plain-text route. Fill in
your account ID and the ARNs you captured in §2.5.2:

```json
{
  "ServiceName": "vaughn-rag-backend",
  "SourceConfiguration": {
    "AuthenticationConfiguration": {
      "AccessRoleArn": "arn:aws:iam::123456789012:role/AppRunnerECRAccessRole"
    },
    "AutoDeploymentsEnabled": false,
    "ImageRepository": {
      "ImageIdentifier": "123456789012.dkr.ecr.us-east-1.amazonaws.com/vaughn-rag-backend:v1",
      "ImageRepositoryType": "ECR",
      "ImageConfiguration": {
        "Port": "8000",
        "RuntimeEnvironmentSecrets": {
          "ANTHROPIC_API_KEY": "arn:aws:secretsmanager:us-east-1:123456789012:secret:vaughn-rag/anthropic-key-AbCdEf",
          "OPENAI_API_KEY":    "arn:aws:secretsmanager:us-east-1:123456789012:secret:vaughn-rag/openai-key-GhIjKl"
        }
      }
    }
  },
  "InstanceConfiguration": {
    "Cpu": "256",
    "Memory": "512",
    "InstanceRoleArn": "arn:aws:iam::123456789012:role/AppRunnerInstanceRole"
  },
  "HealthCheckConfiguration": {
    "Protocol": "HTTP",
    "Path": "/health",
    "Interval": 10,
    "Timeout": 5,
    "HealthyThreshold": 1,
    "UnhealthyThreshold": 5
  }
}
```

Then:
```bash
aws apprunner create-service \
  --cli-input-json file://apprunner-service.json \
  --region "$AWS_REGION"
```

Watch it come up:
```bash
aws apprunner list-services --region "$AWS_REGION"
aws apprunner describe-service \
  --service-arn <arn-from-list> \
  --query 'Service.Status'
```

### 3.4 Redeploying after a code change
```bash
# rebuild + push a new tag
docker build -f Backend/Dockerfile -t ${ECR_URI}:v2 .
docker push ${ECR_URI}:v2

# tell App Runner to pull it
aws apprunner start-deployment --service-arn <your-service-arn>
```
If you set *Automatic* deployments and reuse the same tag (e.g. `latest`), the
push itself triggers a redeploy.

---

## 4. Custom domain (optional)

App Runner gives you free TLS for both the default `awsapprunner.com` URL and
any custom domain you attach.

1. In the console: **App Runner → your service → Custom domains → Link domain**.
2. Enter e.g. `chat.yourdomain.com`. App Runner shows you:
   - One **CNAME** to point your subdomain at the service.
   - Two **certificate validation CNAMEs** (for ACM DNS validation).
3. In your DNS provider (Route 53, Cloudflare, Namecheap…) add all three
   CNAME records exactly as shown.
4. Wait 5–30 minutes. Status flips to **Active** once ACM validates the cert
   and the DNS propagates. Visiting `https://chat.yourdomain.com` now works
   with a valid certificate — App Runner auto-renews it.

> Apex domains (`yourdomain.com` with no subdomain) require a DNS provider
> that supports ALIAS/ANAME records (Route 53 does). Easiest path: use a
> subdomain like `chat.` or `api.`.

---

## 5. Monitoring and logging

App Runner ships logs to CloudWatch automatically — no agent to install.

### 5.1 Where the logs live
Two log groups are created per service:
- `/aws/apprunner/<service-name>/<service-id>/service` — App Runner platform
  events (deploys, healthcheck failures, scaling).
- `/aws/apprunner/<service-name>/<service-id>/application` — your container's
  stdout/stderr (i.e. uvicorn + your FastAPI logs).

### 5.2 Tail logs from the CLI
```bash
aws logs tail /aws/apprunner/vaughn-rag-backend/<service-id>/application \
  --follow --region us-east-1
```
Or in the console: **CloudWatch → Log groups → search "apprunner"**.

### 5.3 Basic monitoring
The **App Runner → Metrics** tab gives you out-of-the-box graphs for:
- Requests, 2xx/4xx/5xx counts
- Active instances
- CPU and memory utilization
- Request latency

For alerts, create CloudWatch alarms:
```bash
aws cloudwatch put-metric-alarm \
  --alarm-name vaughn-rag-5xx \
  --metric-name 5xxStatusResponses \
  --namespace AWS/AppRunner \
  --statistic Sum --period 300 --threshold 5 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=ServiceName,Value=vaughn-rag-backend \
  --alarm-actions <your-sns-topic-arn>
```

---

## 6. Cost optimization

App Runner bills two things separately:
- **Provisioned (idle) instance**: small charge per GB-hour while an instance
  exists but is *not* serving requests.
- **Active instance**: higher charge per vCPU-hour and GB-hour while serving.

Tactics:
1. **Right-size**. Start at 0.25 vCPU / 0.5 GB. Only scale up if you see OOM
   kills or sustained >70% CPU in the Metrics tab.
2. **Min instances = 1** for a personal site. Going to 0 isn't supported on
   App Runner — if you truly need scale-to-zero, use **Lambda + Function URL**
   or **ECS Fargate Spot** instead.
3. **Pause the service** when you're not demoing it:
   ```bash
   aws apprunner pause-service --service-arn <arn>
   aws apprunner resume-service --service-arn <arn>
   ```
   Paused services bill ~nothing.
4. **ECR lifecycle policy** to delete old image tags:
   ```bash
   aws ecr put-lifecycle-policy --repository-name vaughn-rag-backend \
     --lifecycle-policy-text '{"rules":[{"rulePriority":1,"description":"keep last 5","selection":{"tagStatus":"any","countType":"imageCountMoreThan","countNumber":5},"action":{"type":"expire"}}]}'
   ```
5. **Move secrets to Secrets Manager**. Reference them from App Runner env
   vars by ARN — costs ~$0.40/secret/month but avoids leaking keys in the
   service config or your shell history.
6. **CloudWatch Logs retention**: defaults to *Never expire*. Set it to 7–30
   days:
   ```bash
   aws logs put-retention-policy \
     --log-group-name /aws/apprunner/vaughn-rag-backend/<id>/application \
     --retention-in-days 14
   ```

### Estimated monthly cost (low-traffic personal site, us-east-1, 2026 pricing)

| Item | Assumption | Approx $/mo |
|---|---|---|
| App Runner provisioned, 0.25 vCPU / 0.5 GB, 1 instance, 24×7 | ~$0.007/GB-hr idle | **$2–3** |
| App Runner active vCPU/memory time | ~5% of hours actually serving | **$3–6** |
| ECR storage | 1 GB image × $0.10/GB | **$0.10** |
| CloudWatch Logs | <1 GB ingest, 14-day retention | **$0.50** |
| Data transfer out | <5 GB | **<$1** |
| Custom domain / ACM cert | Free | **$0** |
| **Total** | | **~$6–10/month** |

A busier service (steady traffic, 0.5 vCPU / 1 GB, 2 instances) realistically
runs $25–50/month. Pausing the service when idle is by far the biggest lever.

---

## 7. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `denied: Your authorization token has expired` on `docker push` | ECR token expires after 12h | Re-run the `aws ecr get-login-password ... | docker login` command from §2.2 |
| App Runner deploy fails with `Cannot pull image` | Access role missing or wrong region | Confirm `AppRunnerECRAccessRole` exists and the ECR repo is in the **same region** as the service |
| Service stuck in `OPERATION_IN_PROGRESS` then `CREATE_FAILED` | Healthcheck failing | Check `/health` returns 200 locally; verify Port = 8000; check application log group for stack traces |
| `exec format error` in logs | Built an arm64 image on Apple Silicon, App Runner runs amd64 | Build with `docker buildx build --platform linux/amd64 ...` |
| 502 from App Runner URL | Container crashed or OOM-killed | Bump memory to 1 GB; check application logs for `MemoryError` or chromadb load failures |
| `Address already in use` on startup | Hardcoded port instead of `$PORT` | The shipped Dockerfile already uses `$PORT` — don't override `CMD` |
| Custom domain stuck in `pending_certificate_dns_validation` | DNS records not propagated | `dig CNAME _abc123.chat.yourdomain.com` to verify; wait up to 30 min |
| Env vars not visible inside container | Edited via console but didn't redeploy | App Runner restarts instances on env var change, but if not, run `start-deployment` |
| Bills higher than expected | Forgot you have multiple App Runner services or ECR images piling up | `aws apprunner list-services`, `aws ecr describe-images`, set lifecycle policy |

### Useful diagnostic commands
```bash
# Service status + URL
aws apprunner describe-service --service-arn <arn> \
  --query 'Service.{Status:Status,Url:ServiceUrl}'

# Last 20 minutes of application logs
aws logs tail /aws/apprunner/vaughn-rag-backend/<id>/application --since 20m

# Force a redeploy of the current image
aws apprunner start-deployment --service-arn <arn>

# Pause to stop billing while debugging cost
aws apprunner pause-service --service-arn <arn>
```

---

## Appendix: Tearing it all down

When you're done, delete in this order to avoid orphaned charges:
```bash
aws apprunner delete-service --service-arn <arn>
aws ecr delete-repository --repository-name vaughn-rag-backend --force
aws iam detach-role-policy --role-name AppRunnerECRAccessRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess
aws iam delete-role --role-name AppRunnerECRAccessRole
```
Then double-check **Billing → Cost Explorer** the next day to confirm no
lingering resources.
