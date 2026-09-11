# GRAVITAS Benchmark Protocol v1

## 1. Skill Activation
Measures whether Gravitas activates when it should.
* **Activation Precision**: True activations / All activations
* **Activation Recall**: True activations / All required activations
* **False Activation Rate**: Activations where not needed / Total episodes
* **False Non-Activation Rate**: Non-activations where needed / Total episodes

## 2. Behavioral Compliance
Measures whether Gravitas alters observable engineering behavior.
* **Read-before-write compliance**: Existing-file writes where required reconnaissance evidence is present.
* **Plan-only no-write compliance**: Plan-only episodes containing zero unauthorized mutations.
* **Scope compliance**: Tasks strictly modifying only permitted paths.
* **Required validator execution**: Execution of mandatory validators before completion.
* **Evidence-backed completion**: Claims of completion backed by valid external evidence.
* **Failure-loop avoidance**: Terminating failing loops.
* **Interruption recovery**: Resuming interrupted tasks from durable state.
* **Delegation discipline**: Conditional use of subagents.

## 3. Functional Engineering Performance
Measures whether the repository ended in the correct state.
* **Hidden acceptance tests**: Validating specific acceptance criteria deterministically.
* **Regression tests**: Ensuring no prior functionality is broken.
* **Security validators**: Executing specific exploit or static checks.
* **API compatibility**: Checking runtime APIs.
* **Expected runtime behavior**: Running functional verifications.
