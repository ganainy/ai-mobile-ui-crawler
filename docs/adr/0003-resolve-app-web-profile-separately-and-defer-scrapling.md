# Resolve App Web Profile separately from App Metadata, and defer scrapling

Guided Scenario generation needs to know what a target app actually does, so we added Web Profile Resolution: a Play Store description lookup (reusing `google_play_scraper`, already a dependency) plus optional plain-`requests` text scraping of the app's developer website. We kept this as a resolver sibling to `AppMetadataResolver` rather than extending it, even though both call the same Play Store API — `AppMetadataResolver` answers a display question (label/icon, keyed by installed versionCode via Local Resolution) while Web Profile Resolution answers a content question (what does this app do, keyed by package alone, no Local Resolution path) feeding a completely different consumer (Guided Scenario generation vs. the app picker). The cost is one extra Play Store call per app; the benefit is the two resolvers' failure modes and cache lifecycles stay independent.

For the website-enrichment step we chose a plain `requests` GET over `scrapling` (the tool originally proposed for this feature), on the bet that developer marketing pages are usually static enough — and deferred the heavier, JS-rendering-capable dependency until we have evidence it's needed. Fetch failures are logged rather than silently swallowed, specifically to accumulate that evidence.

## Considered options for the website step

- **scrapling from the start** — handles JS-rendered/anti-bot sites, but is a heavier dependency for what's an optional enrichment source (the Play Store description is primary). Rejected for now; failure logging is the tripwire to revisit.
- **Extend `AppMetadataResolver` to also return description/site text** — avoids a second Play Store call, but conflates a display-metadata resolver with a content-scraping one whose consumers and failure handling don't overlap. Rejected in favor of a sibling class.
