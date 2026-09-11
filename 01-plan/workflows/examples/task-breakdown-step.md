# Example: Task Breakdown & DAG Construction

<!-- @verifies REQ-TASK-01 -->
<!-- @verifies REQ-TASK-02 -->
<!-- @verifies REQ-TASK-04 -->

This example demonstrates how an agent authors atomic tasks and configures dependencies for topological scheduling.

```markdown
### [TASK-01] Database Schema Migration
- **Wave**: 1
- **Dependencies**: `[]`
- **Component / Layer**: Infrastructure / Persistence
- **Files to Touch**:
  - `src/Infrastructure/Data/Migrations/001_Initial.sql`
  - `src/Infrastructure/Data/AppDbContext.cs`

#### Description
Create the initial database migration adding the `TodoLists` and `TodoItems` tables with foreign key constraints.

#### Definition of Done (DoD)
- [ ] Migration script compiles and applies cleanly
- [ ] Rollback script drops created tables

#### Verification Criteria (`03-qa`)
- **Action**: SQL Table Verification
- **Expected Outcome**: Table `TodoLists` exists with columns `Id`, `Title`, `CreatedAt`

---

### [TASK-02] Repository & Service Implementation
- **Wave**: 2
- **Dependencies**: `[TASK-01]`
- **Component / Layer**: Application / Domain
- **Files to Touch**:
  - `src/Domain/Entities/TodoList.cs`
  - `src/Application/Services/TodoListService.cs`

#### Description
Implement the core domain entity and domain service for managing todo lists.

#### Definition of Done (DoD)
- [ ] Unit tests for `TodoListService` pass with >90% coverage
- [ ] Validations reject empty titles

#### Verification Criteria (`03-qa`)
- **Action**: Unit Test Suite
- **Expected Outcome**: `dotnet test --filter Category=Unit` passes 100%
```
