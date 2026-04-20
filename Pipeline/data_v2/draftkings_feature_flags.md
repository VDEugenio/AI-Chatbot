---
name: DraftKings Feature Flagging Strategy
description: Feature flag implementation stored in app settings — safe rollouts, Redis caching toggles, emergency kill switches, and gradual production enablement pattern.
company: draftkings
topics: [feature_flags, safe_rollouts, kill_switches, ab_testing, progressive_delivery]
skills: [feature_flags, redis, deployment_strategy]
story_types: [efficiency, problem_solving, systems_thinking]
---

### Feature Flagging Strategy

#### Implementation
- **Storage:** Feature flags stored in app settings (not external service like LaunchDarkly)
- **Configuration:** Flags set per environment (dev, staging, prod)
- **Granularity:** Could enable/disable entire features or individual sub-features

#### Use Cases

**1. Safe Rollouts**
- Enable new features gradually (e.g., start with 10% of users, ramp to 100%)
- Test features in production with limited exposure
- Quick rollback capability if issues arise

**2. Redis Caching Toggles**
- Feature flag to enable/disable Redis caching per service
- Allowed A/B testing of caching strategies
- Enabled quick disabling if cache corruption occurred

**3. Emergency Kill Switches**
- If a feature caused production issues, could disable via flag without redeploying
- Critical for time-sensitive DFS workflows where downtime = lost revenue

**Example Scenario:**
- Deploy major feature to prod with flag OFF
- Gradually enable for internal testing
- Enable for 10% of users
- Monitor Datadog metrics (error rates, latency, throughput)
- If metrics look good → ramp to 100%
- If issues arise → disable flag immediately, investigate offline
