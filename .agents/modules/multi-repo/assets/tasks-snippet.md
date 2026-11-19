Add these fields to each task; `Depends on` remains the complete dependency list.

- Repository: <one configured Repository ID>
- Cross-repo depends on: <unique exact cross-repository subset of Depends on, or none>
- Integration evidence: <planned procedure, observed reference, or none when no cross-repo dependency>
- Dirty status: clean | dirty-nonconflicting | blocked-conflict | unknown
- Ownership/isolation: exclusive-owner | isolated | blocked-conflict | unknown

`ready`, `in-progress`, and `done` require a non-blocking value for both controls.
When a `blocked` task uses `blocked-conflict` or `unknown`, add the exact matching
`Blocker` reference: `dirty-status:<value>` and/or
`ownership-isolation:<value>`. Other blockers, such as dependency IDs, remain
valid and do not replace a required matching control reference.
