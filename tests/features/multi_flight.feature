Feature: multi-flight interactions

  With several flights the bands combine, nearly-parallel lines pinch off
  slivers, and corners survive only where every band misses. Expected
  results follow the infinite-band model and are re-checked by the
  independent oracle on every run (plan §9.1).

  Scenario Outline: a flight band that already covers the whole square
    Given a square with side 100 km
    Given a flight from (<x0a>, <y0a>) to (<x1a>, <y1a>)
    And a flight from (<x0b>, <y0b>) to (<x1b>, <y1b>)
    And the program runs
    And the run should finish within 10 seconds
    Then the result should be OK
    And the whole square should be viewed

    Examples: one band spans the square edge to edge
      | x0a | y0a | x1a  | y1a  | x0b | y0b | x1b  | y1b  |
      | 50  | 0   | 50   | 100  | 0   | 50  | 100  | 50   |
      | 50  | 0   | 50   | 100  | 0   | 0   | 100  | 100  |
      | 50  | 0   | 50   | 100  | 0   | 40  | 100  | 40   |
      | 0   | 50  | 100  | 50   | 0   | 40  | 100  | 40   |
      | 0   | -50 | 100  | -50  | 0   | 50  | 100  | 50   |
      | 50  | 0   | 50   | 100  | -30 | -30 | 130  | 130  |

  Scenario Outline: parallel pairs leave an uncovered strip
    Given a square with side 100 km
    Given a flight from (<x0a>, <y0a>) to (<x1a>, <y1a>)
    And a flight from (<x0b>, <y0b>) to (<x1b>, <y1b>)
    And the program runs
    And the run should finish within 10 seconds
    Then the result should be a point
    And the result should be a point at least 50 km from every flight

    Examples: strips of various widths near a corner
      | x0a | y0a | x1a | y1a | x0b | y0b  | x1b | y1b  |
      | 0   | 30  | 100 | 30  | 0   | 45   | 100 | 45   |
      | 0   | 30  | 100 | 30  | 0   | 40   | 100 | 40   |
      | 0   | -20 | 100 | -20 | 0   | 0    | 100 | 0    |
      | 0   | 30  | 100 | 30  | 0   | 30.5 | 100 | 30.5 |
      | -60 | -20 | 60  | -20 | -60 | 0    | 60  | 0    |

    Examples: perpendicular pair missing one corner
      | x0a | y0a | x1a | y1a | x0b | y0b | x1b | y1b |
      | 0   | 30  | 100 | 30  | 30  | 0   | 30  | 100 |
      | -20 | 0   | -20 | 100 | 0   | -20 | 100 | -20 |
      | 0   | -20 | 100 | -20 | 40  | -20 | 40  | 120 |

  Scenario Outline: three flights, corner survives all bands
    Given a square with side 100 km
    Given a flight from (<x0a>, <y0a>) to (<x1a>, <y1a>)
    And a flight from (<x0b>, <y0b>) to (<x1b>, <y1b>)
    And a flight from (<x0c>, <y0c>) to (<x1c>, <y1c>)
    And the program runs
    And the run should finish within 10 seconds
    Then the result should be a point
    And the result should be a point at least 50 km from every flight

    Examples: strips of various widths near a corner
      | x0a | y0a | x1a | y1a | x0b | y0b | x1b | y1b | x0c | y0c | x1c | y1c |
      | 0   | 30  | 100 | 30  | 30  | 0   | 30  | 100 | 0   | -30 | 100 | -30 |
      | 0   | 40  | 100 | 40  | 40  | 0   | 40  | 100 | 0   | -30 | 100 | -30 |
