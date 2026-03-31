meta:
  format: "4d-design-rules"
  version: 1

spacingSystem:
  baseUnit: 4
  allowedValues: [4, 8, 12, 16, 24]

window:
  padding:
    top: 16
    left: 16
    right: 16
    bottom: 16

alignment:
  default: "left"
  rules:
    - all_inputs_align_left
    - labels_align_with_inputs
    - avoid_mixed_alignment

buttons:
  spacing:
    horizontal: [8, 12]
    vertical: [8, 12]

  grouping:
    primary_far_from_secondary: true

forms:
  verticalSpacing: [10, 12, 16]
  labelToInputSpacing: [4, 8]

constraints:
  - no_overlap
  - consistent_spacing
  - align_to_grid