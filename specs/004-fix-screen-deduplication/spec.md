# Feature Specification: Fix Screen Deduplication

**Feature Branch**: `004-fix-screen-deduplication`  
**Created**: 2026-01-11  
**Status**: Draft  
**Input**: Bug fix for screen deduplication issue where minor visual changes (rotating carousels, dynamic content) cause false-positive unique screen detection

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Accurate Unique Screen Detection (Priority: P1)

As a crawler operator, I want the screen tracker to correctly identify unique screens based on structural similarity rather than exact visual matching, so that rotating carousels, dynamic banners, and minor visual changes don't create false-positive unique screen counts.

**Why this priority**: This is the core fix. The current system reports 8 unique screens when only 2-3 actually exist due to home screen carousel rotations being treated as new screens. This fundamentally breaks exploration metrics and AI decision-making.

**Independent Test**: Run the crawler on an app with a home screen containing a rotating carousel banner. After 10 steps visiting the home screen multiple times with different carousel slides, the reported unique screen count should match the actual distinct screen contexts (±1).

**Acceptance Scenarios**:

1. **Given** the crawler is on a home screen with a rotating carousel, **When** the carousel rotates to show different promotional banners, **Then** the system recognizes it as the same screen (not a new unique screen)
2. **Given** the crawler captures a screenshot with status bar showing time "10:30", **When** a subsequent screenshot shows time "10:31" on the same screen, **Then** the system recognizes it as the same screen
3. **Given** the crawler visits the home screen 6 times during a session, **When** the unique screens are counted, **Then** the home screen contributes exactly 1 to the unique screen count

---

### User Story 2 - Meaningful Screen Similarity Threshold (Priority: P2)

As a crawler operator, I want to configure the similarity threshold for screen deduplication, so that I can tune the sensitivity based on the specific app being tested.

**Why this priority**: Different apps have different levels of visual dynamism. A configurable threshold allows operators to balance between over-deduplication (grouping genuinely different screens) and under-deduplication (treating same screens as different).

**Independent Test**: Modify the similarity threshold configuration, run the crawler, and verify that the unique screen detection behavior changes appropriately with different threshold values.

**Acceptance Scenarios**:

1. **Given** a similarity threshold of 85%, **When** two screens are 90% similar, **Then** they are treated as the same screen
2. **Given** a similarity threshold of 85%, **When** two screens are 80% similar, **Then** they are treated as different screens
3. **Given** no explicit threshold configuration, **When** the crawler runs, **Then** a reasonable default threshold is used (suggested: 85-90%)

---

### User Story 3 - Correct Exploration Novelty Signals (Priority: P2)

As the AI exploration agent, I need accurate "is this a new screen?" signals, so that my exploration decisions are based on reality rather than false positives caused by dynamic content.

**Why this priority**: The AI uses screen novelty to guide exploration. False positives make the AI think it's making progress when it's actually stuck in a loop, leading to poor exploration coverage.

**Independent Test**: Observe AI decision logs during a crawl session. When the crawler revisits the same screen (but with different carousel state), the novelty signal should indicate "same screen" rather than "new screen".

**Acceptance Scenarios**:

1. **Given** the AI just performed a swipe on the home screen, **When** the carousel animates to show a new slide, **Then** the exploration journal reports returning to a known screen (not discovering a new one)
2. **Given** the AI has visited the search results screen with query "vitaminsaft", **When** it visits search results with query "redcare", **Then** the system may optionally treat this as the same screen type (configurable behavior)

---

### User Story 4 - Accurate Exploration Metrics (Priority: P3)

As a crawler operator reviewing run results, I want the "unique screens visited" metric to reflect actual distinct screen contexts, so that I can trust the reported metrics for evaluating exploration effectiveness.

**Why this priority**: Metrics drive decisions. Inflated unique screen counts give false confidence and make it impossible to identify when the crawler is underperforming.

**Independent Test**: After a completed run, manually review screenshots and count distinct screen contexts. Compare to the reported "unique_screens_visited" metric. They should match within ±1.

**Acceptance Scenarios**:

1. **Given** Run #88 with 10 screenshots showing 2-3 actual screen contexts, **When** the run summary is generated, **Then** unique_screens_visited reports 2-3 (not 8)
2. **Given** a run export JSON, **When** reviewed by a human, **Then** the unique screen count matches visual observation

---

### Edge Cases

- What happens when the screen is completely blank (loading state)?
- How does the system handle screens with very similar layouts but fundamentally different purposes (e.g., Login vs Registration forms)?
- What happens during animated transitions captured mid-animation?
- How are permission dialogs and system overlays handled (same base screen with overlay)?
- What if two genuinely different screens happen to be perceptually similar?

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST use perceptual hashing (pHash, dHash, or similar) instead of exact image hashing for screen comparison
- **FR-002**: System MUST treat screenshots with Hamming distance below the configured threshold as the same screen
- **FR-003**: System MUST provide a configurable similarity threshold with a sensible default (suggested: 85-90% similarity, or Hamming distance < 10 for 64-bit hash)
- **FR-004**: System MUST exclude or weight down known dynamic regions (status bar) in the similarity calculation
- **FR-005**: System MUST correctly update the unique screen count in run metrics based on perceptual deduplication
- **FR-006**: System MUST clear existing screen data or re-initialize the database to support the new hashing algorithm (backward compatibility NOT required)
- **FR-007**: System SHOULD log similarity scores between consecutive screens for debugging purposes
- **FR-008**: System SHOULD expose the perceptual hash of each screen for debugging and analytics

### Key Entities

- **Screen**: A distinct app context/page identified by its perceptual hash and considered unique when sufficiently different from all previously seen screens
- **ScreenHash**: A perceptual hash fingerprint (e.g., 64-bit) derived from the screenshot image, tolerant to minor visual variations
- **SimilarityThreshold**: Configuration value defining when two screen hashes are considered "same screen" (Hamming distance or percentage)

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For a run with N manually-verified distinct screens, the system reports unique_screens_visited within ±1 of N
- **SC-002**: Home screens with rotating carousel content are correctly deduplicated 100% of the time
- **SC-003**: Status bar changes (time, battery, signal) do not cause false-positive unique screen detection
- **SC-004**: The AI exploration journal correctly reflects "revisiting known screen" when returning to previously visited screens with minor visual changes
- **SC-005**: Run #88 scenario (previously 8 reported, actual 2-3) would report 2-3 unique screens after the fix
- **SC-006**: Perceptual hash calculation adds less than 50ms per screenshot (performance requirement)


## Clarifications

### Session 2026-01-11
- Q: How to handle backward compatibility with existing pHash (256-bit) data when moving to dHash (64-bit)? → A: Clear Database (Option C). The user explicitly requested to delete old data and use the new approach without backward compatibility concerns.

## Assumptions
- The ImageHash library (or similar) is available or can be added as a dependency
- Status bar region dimensions are reasonably consistent across devices (approximately top 80-120 pixels)
- The current screen tracking logic can be modified without breaking dependent components
- A single perceptual hashing algorithm (pHash recommended) will be sufficient for most app types
- The default similarity threshold will work well for 90%+ of apps without manual tuning
