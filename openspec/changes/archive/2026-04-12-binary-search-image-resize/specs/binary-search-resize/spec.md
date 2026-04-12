## ADDED Requirements

### Requirement: Binary search convergence on scale factor
The system SHALL use binary search on scale factor to find an output size within the target band. The initial guess SHALL be computed as `sqrt(max_size_bytes / original_file_size)`, clamped to `[0.1, 1.0]`. The search space SHALL be `lo=0.1`, `hi=1.0`.

#### Scenario: Large JPEG resized into target band
- **WHEN** a 2000x2000 JPEG image exceeding the size limit is resized with a given max_size_bytes
- **THEN** the output file size SHALL be between 90% and 100% of max_size_bytes

#### Scenario: Large PNG resized into target band
- **WHEN** a 2000x2000 PNG image exceeding the size limit is resized with a given max_size_bytes
- **THEN** the output file size SHALL be between 90% and 100% of max_size_bytes

#### Scenario: Large WEBP resized into target band
- **WHEN** a 2000x2000 WEBP image exceeding the size limit is resized with a given max_size_bytes
- **THEN** the output file size SHALL be between 90% and 100% of max_size_bytes

### Requirement: Fixed compression quality for lossy formats
The system SHALL use a fixed quality of 90 for JPEG and WEBP encoding. PNG encoding SHALL NOT use a quality parameter (lossless).

#### Scenario: JPEG encoded at quality 90
- **WHEN** a JPEG image is resized
- **THEN** the output SHALL be encoded with quality=90 and optimize=True

#### Scenario: PNG encoded without quality parameter
- **WHEN** a PNG image is resized
- **THEN** the output SHALL be encoded with optimize=True and no quality parameter

### Requirement: Early return for under-limit files
The system SHALL return the original file path unchanged when the original file size is already within the size limit.

#### Scenario: Small file returns original path
- **WHEN** resize_file is called with an image whose file size is already under max_size_bytes
- **THEN** the original input_path SHALL be returned without re-encoding

### Requirement: Minimum dimension guard
The system SHALL stop searching and return best effort when either dimension of the scaled image would fall below 64 pixels.

#### Scenario: Image hits minimum dimension during search
- **WHEN** binary search reaches a scale factor where either width or height would be below 64px
- **THEN** the system SHALL stop the search and return the best under-limit result seen so far, or the closest result overall

### Requirement: Iteration safety cap
The system SHALL stop after a maximum of 10 iterations and return the best result available.

#### Scenario: Safety cap reached
- **WHEN** the binary search has not converged after 10 iterations
- **THEN** the system SHALL return the best under-limit result, or the closest result overall, or raise a ValidationError if no result was produced

### Requirement: Best-effort fallback
The system SHALL track the best under-limit result and the best overall result during the search. When the search ends without landing in the target band, the system SHALL prefer the best under-limit result, then the best overall result, and only raise ValidationError as a last resort.

#### Scenario: No result in target band but under-limit result exists
- **WHEN** the search ends and no result landed in the 90-100% band but a result under the limit was found
- **THEN** the system SHALL return the best under-limit result

#### Scenario: No under-limit result exists
- **WHEN** the search ends and no result was under the limit
- **THEN** the system SHALL return the smallest result seen overall

#### Scenario: No result produced at all
- **WHEN** the search ends with no results (e.g., image too small to encode)
- **THEN** the system SHALL raise a ValidationError with error code INVALID_IMAGE_SIZE
