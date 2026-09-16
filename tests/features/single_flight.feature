Feature: single-flight coverage of a square

  A plane crosses a square in one straight flight (x0,y0)->(x1,y1), viewing a
  50 km band each side of its infinite line. A point is unviewed when its
  perpendicular distance to the line exceeds 50 km. The program reports
  either OK (whole square viewed), ERROR (invalid input), or an uncovered
  point. With one flight the band is 100 km wide, so only an exactly
  centered axis-parallel line can view the whole 100 km square.

  Background:
    Given a square with side 100 km

  Scenario Outline: oblique or off-center flight leaves a point unviewed
    Given a flight from (<x0>, <y0>) to (<x1>, <y1>)
    And the program runs
    And the run should finish within 10 seconds
    Then the result should be a point
    And the result should be a point at least 50 km from every flight

    Examples: corner-to-corner diagonals
      | x0 | y0  | x1  | y1  |
      | 0  | 0   | 100 | 100 |
      | 0  | 100 | 100 | 0   |
      | 10 | 10  | 90  | 85  |
      | 0  | 0   | 100 | 35  |

    Examples: chords that stay well inside the square
      | x0 | y0 | x1 | y1 |
      | 20 | 20 | 80 | 80 |
      | 10 | 90 | 90 | 90 |
      | 45 | 0  | 55 | 100 |

    Examples: short segments near the middle
      | x0 | y0 | x1   | y1 |
      | 40 | 20 | 60   | 20 |
      | 50 | 40 | 50.5 | 60 |

    Examples: edge-hugging axis-parallel lines
      | x0 | y0 | x1  | y1 |
      | 0  | 0  | 100 | 0  |
      | 0  | 1  | 100 | 1  |
      | 0  | 0  | 0   | 100 |
      | 0  | 0  | 50  | 0  |

    Examples: lines outside the square (infinite line still counts)
      | x0  | y0  | x1  | y1 |
      | -60 | -60 | -20 | -20 |
      | 160 | 160 | 200 | 200 |
      | -100 | -60 | 0 | -60 |
      | 200 | -50 | 200 | 50 |

  Scenario Outline: centered axis-parallel flight views the whole square
    Given a flight from (<x0>, <y0>) to (<x1>, <y1>)
    And the program runs
    And the run should finish within 10 seconds
    Then the result should be OK
    And the whole square should be viewed

    Examples: band edges exactly on the square edges
      | x0    | y0 | x1    | y1   |
      | 50    | 0  | 50    | 100  |
      | 50    | -5 | 50    | 105  |
      | 0     | 50 | 100   | 50   |
      | -5    | 50 | 105   | 50   |
      | 49.75 | 50 | 50.25 | 50   |
      | 50    | 50 | 50.01 | 50   |
