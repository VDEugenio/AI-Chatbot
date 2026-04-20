---
name: DraftKings Performance and Scale
description: Traffic patterns for 500k+ peak users, Redis caching for player cards, DB query optimization, and seasonal Kubernetes scaling strategies.
company: draftkings
topics: [performance_optimization, caching, database_optimization, kubernetes_scaling, traffic_forecasting, seasonal_variance]
skills: [redis, kubernetes, sql_optimization, caching_strategy]
story_types: [performance_optimization, efficiency, systems_thinking]
related_files: [draftkings_architecture.md]
---

## Performance & Scale

### Traffic Patterns
- **Peak Users:** 500,000+ daily active users during peak seasons
- **Seasonal Variance:** Traffic varies drastically by sport season
  - **High Traffic:** Week 1 NFL, playoff seasons, major sporting events
  - **Low Traffic:** Off-seasons (e.g., NFL off-season)
- **Throughput:** Systems designed to handle high-volume, time-sensitive workflows

### Performance Optimization Work

#### Redis Caching Implementation
- **Use Case:** Player card data during drafts
- **Problem:** Many users querying same player stats simultaneously during draft windows
- **Solution:** Cached frequently-requested player card data to reduce database load and improve response times
- **Impact:** Reduced resource usage, faster player card load times

#### Database Query Optimization
- **Approach:** Made more specific database calls to retrieve only necessary data
- **Techniques:**
  - Narrowed SELECT statements to required columns
  - Leveraged cached data where appropriate
  - Reduced payload sizes
- **Result:** More efficient database calls, improved query performance

#### Kubernetes Scaling
- **Approach:** Scaled workloads up/down based on seasonal traffic forecasts
- **Process:** Manual scaling adjustments to match predicted demand
- **Example:** Scale up before Week 1 NFL, scale down during off-season
- **Impact:** Maintained platform stability during peak demand while optimizing costs during low-traffic periods
