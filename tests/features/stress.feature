@timing
Feature: performance envelope

  Every scenario is timed; the timing table printed at the end of the run
  reports per-scenario time, and this feature pins the N=100 worst cases to
  the 10 s limit from plan §9.3. These carry the @timing tag so they can be
  run alone with --tags @timing. The oracle re-checks each answer, so a
  PASS also means the reported outcome (OK / point / ERROR) is genuinely
  valid for the generated input.

  Scenario Outline: N=100 stress inputs
    Given a stress input with 100 flights and side <L> km (seed 20260916)
    And the program runs
    And the run should finish within 10 seconds
    Then the run should produce a well-formed answer

    Examples: largest, smallest, and nominal squares
      | L    |
      | 1000 |
      | 1    |
      | 100  |
