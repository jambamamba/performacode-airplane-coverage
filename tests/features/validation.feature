Feature: input validation (policy A-2)

  The program accepts one real L in (0, 1000], then an integer N in [1, 100],
  then exactly 4*N finite coordinates with (x0,y0) != (x1,y1), and nothing
  else. Any violation prints ERROR.

  # The \n sequences below stand for newlines in the INPUT file.

  Scenario Outline: malformed or out-of-range inputs are rejected
    Given the malformed input "<text>"
    And the program runs
    And the run should finish within 10 seconds
    Then the result should be ERROR

    Examples: every rejection class
      | text                       | reason                        |
      | abc 1 0 0 5 5              | non-numeric L                 |
      | 0 1 0 0 5 5                | L below range                 |
      | 1001 1 0 0 5 5             | L above range                 |
      | nan 1 0 0 5 5              | NaN L                         |
      | 100                        | missing N                     |
      | 100 0 0 0 5 5              | N below range                 |
      | 100 101 0 0 5 5            | N above range                 |
      | 100 1 0 0 5                | truncated coordinates         |
      | 100 1 0 0 5 5 99           | extra token after last flight |
      | 100 1 0 0 5 5 0 0 3 3      | more flights than N declares  |
      | 100 1 5 5 5 5              | coincident endpoints          |
      | 100 1 0 nan 5 5            | NaN coordinate                |
      |                            | empty input                   |
