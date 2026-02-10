# Consistency Scoring Rubric

Score each layer 0-100.

## Main Conclusion
- 90-100: same conclusion with wording differences only
- 70-89: same trend but notable emphasis shift
- 40-69: partial contradiction
- 0-39: clear contradiction

## Advice Direction
- 90-100: same action direction
- 70-89: mostly same with minor tactic changes
- 40-69: mixed direction
- 0-39: opposite direction

## Risk Disclaimer
- 90-100: same risk level and warning type
- 70-89: warning present but weaker/stronger than expected
- 0-69: warning missing or inappropriate

Final score:
- `0.5 * conclusion + 0.3 * advice + 0.2 * risk`

Release gate recommendation:
- >=85 pass
- 70-84 conditional pass with mitigation
- <70 fail
