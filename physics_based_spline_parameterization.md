# Physics-Based Spline Parameterization

## Core Problem

Splines define geometric paths through space but contain no inherent timing information. For realistic flight simulation, we need to incorporate physics to determine *when* an aircraft reaches each point along the path, not just *where* it goes.

## Key Insight: Separation of Geometry and Timing

**Without physics:**
- Position is simply a function of time: `position = spline(t)`
- Movement along the spline is uniform or arbitrarily parameterized

**With physics:**
- Geometry (the spline) defines the spatial path
- Physics determines velocity, which controls progression along that path
- The spline parameter becomes implicitly coupled to multiple kinematic factors

## The Coupled System

Instead of directly mapping time to position, we solve a coupled dynamic system:

1. **Position** is determined by the spline parameter: `position = spline(s)`
2. **Parameter evolution** is driven by velocity: `ds/dt = velocity / ||dP/ds||`
3. **Velocity** is governed by physics (forces, constraints, terrain)

This creates a feedback loop:
- Current position determines local conditions (slope, altitude)
- Local conditions affect achievable velocity (climbing reduces speed)
- Velocity determines how fast we progress along the spline
- Progress updates position, completing the loop

## Critical Conversion: Parameter Space to Physical Space

**The magnitude ||dP/ds||** acts as a conversion factor:
- Represents how much physical distance corresponds to a unit change in spline parameter
- Computed as: `sqrt((dx/ds)² + (dy/ds)² + (dz/ds)²)`
- Essential for translating velocity (physical units) into parameter progression

**Example calculation:**
```
If ||dP/ds|| = 5 meters per parameter unit
And velocity = 10 m/s
And Δt = 0.1 seconds
Then physical distance = 1 meter
And parameter change Δs = 1/5 = 0.2
```

## Numerical Integration Challenges

**Critical limitation:** This approach requires small, consistent time steps.

**Why:** If Δt is too large:
- Conditions (slope, curvature, forces) may change significantly between s₀ and s₁
- Velocity calculated at s₀ becomes invalid for the path segment
- Can violate physical constraints or produce unrealistic behavior
- May "skip over" important path features like sharp turns or steep climbs

**Best practice:** Keep Δt small enough that velocity and terrain conditions change by less than 10-20% per step.

## Implementation Approach

For each simulation step:
1. Start at current parameter `s₀` with velocity `v₀`
2. Evaluate local path properties: tangent, slope, curvature
3. Compute forces and determine achievable velocity `v₁`
4. Calculate parameter increment: `Δs = (v₁ · Δt) / ||dP/ds||`
5. Update position: `s₁ = s₀ + Δs`
6. Repeat

This naturally produces physically realistic behavior where the aircraft slows on climbs, accelerates on descents, and adjusts speed through curves.
