# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](http://keepachangelog.com/en/1.0.0/)
and this project adheres to [Semantic Versioning](http://semver.org/spec/v2.0.0.html).

<!-- insertion marker -->
## Unreleased

<small>[Compare with latest](https://github.com/mjanez/ckanext-scheming_dcat/compare/v4.3.0...HEAD)</small>

<!-- insertion marker -->
## [v4.3.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v4.3.0) - 2024-12-12

<small>[Compare with v4.2.3](https://github.com/mjanez/ckanext-scheming_dcat/compare/v4.2.3...v4.3.0)</small>

### Added

- Add HVD category and applicable legislation to all INSPIRE records & fix bug ([886c58e](https://github.com/mjanez/ckanext-scheming_dcat/commit/886c58e291ab8722988f06c869c9787f82428359) by mjanez).
- Add root user option to GitHub Actions workflow container ([510fcfc](https://github.com/mjanez/ckanext-scheming_dcat/commit/510fcfc1e88571fd721f5c5d0fc2c14fea5ae02c) by mjanez).
- Add CSW harvester to the list of available harvesters ([66f4ad1](https://github.com/mjanez/ckanext-scheming_dcat/commit/66f4ad15d684e94d3b25be58c41f6540196e7c1c) by mjanez).
- Add temporal and spatial resolution fields to DCAT-AP 2 profiles ([fe9bf54](https://github.com/mjanez/ckanext-scheming_dcat/commit/fe9bf542a371c39f556872541c80b25c0a374581) by mjanez).
- Add schema  to additional_info template to avoid bugs ([277553f](https://github.com/mjanez/ckanext-scheming_dcat/commit/277553faad8b3fe8d412480839bf0b64f245b5d4) by mjanez).
- Add about and harvest info templates for dataset sources ([98fdce6](https://github.com/mjanez/ckanext-scheming_dcat/commit/98fdce659c54927614279c3d8d0eff7cb7cedf7e) by mjanez).

### Fixed

- FIx resource_read template ([e4da5d6](https://github.com/mjanez/ckanext-scheming_dcat/commit/e4da5d64c250972e34e33cf0b189fb1d608bde74) by mjanez).
- Fix bug when source_date_format is None. ([1b25c9e](https://github.com/mjanez/ckanext-scheming_dcat/commit/1b25c9eb71521e4b046b003ae5830b8316444a2a) by mjanez).
- Fix image ([0122653](https://github.com/mjanez/ckanext-scheming_dcat/commit/0122653135e5ba2222a66507c2b042ef568b086f) by mjanez).
- Fix image url ([325a0c2](https://github.com/mjanez/ckanext-scheming_dcat/commit/325a0c220938ee49f06e77ca48d666db98a4b92b) by mjanez).
- Fix GeoDCAT-AP Schemas ([64f6e28](https://github.com/mjanez/ckanext-scheming_dcat/commit/64f6e28fa46a6b5ffdaea99a6a2c9c0dbd5d599b) by mjanez).
- Fix formatting in __init__.py by adding a trailing comma for EuGeoDCATAP3Profile ([980edd2](https://github.com/mjanez/ckanext-scheming_dcat/commit/980edd28d9521da3a395a17e320915b15c82a14c) by mjanez).
- Fix language priorities retrieval to handle non-string values ([1fefbab](https://github.com/mjanez/ckanext-scheming_dcat/commit/1fefbaba0c5d09eb067400fb0e8c7649163e9a7a) by mjanez).

### Removed

- Remove unnecessary multilang flag from _add_triples_from_dict method in EsNTIRISPProfile (es_dcat) ([b6f65e1](https://github.com/mjanez/ckanext-scheming_dcat/commit/b6f65e198db5a037b2e4de292840f52543944f1e) by mjanez).
- Remove unncesary multilang methods since ckanext-dcat v2.1.0 ([e7eff22](https://github.com/mjanez/ckanext-scheming_dcat/commit/e7eff2200894c557057be13d8c5a150f3c9ce0ed) by mjanez).

## [v4.2.3](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v4.2.3) - 2024-11-19

<small>[Compare with v4.2.2](https://github.com/mjanez/ckanext-scheming_dcat/compare/v4.2.2...v4.2.3)</small>

### Added

- Add UUID generation for dataset identifiers instead of adhoc generation and improve logging for harvesters ([41fb759](https://github.com/mjanez/ckanext-scheming_dcat/commit/41fb7590c3eeb0045891484e653cb5b9b4a2e497) by mjanez).
- Add new preset for optional date validation in default_presets.json ([4ebbb30](https://github.com/mjanez/ckanext-scheming_dcat/commit/4ebbb3022a46aebc7814e34fe191dd27674dee9b) by mjanez).
- Add private_fields logic to package_show, package_search, etc. and config options ([ad8172d](https://github.com/mjanez/ckanext-scheming_dcat/commit/ad8172dae84714f970057fe516a8d75f40ed9865) by mjanez).
- Add validators and presets for tag_string normalization (normalize_tag_string_autocomplete) ([e606499](https://github.com/mjanez/ckanext-scheming_dcat/commit/e606499c8f3300d15fda9b20446dfff371478ac1) by mjanez).
- Add custom identifier template and update translations for metadata completion message ([eba6c0d](https://github.com/mjanez/ckanext-scheming_dcat/commit/eba6c0dea0d3ad690979f8e552374f0cfbc421c4) by mjanez).

### Fixed

- Fix Spanish label for dataset author field in schemas ([be095dd](https://github.com/mjanez/ckanext-scheming_dcat/commit/be095ddbf76323f79d72eddcca7d192d043faa12) by mjanez).
- Fix user organization membership check and clean up tag normalization logging ([404b838](https://github.com/mjanez/ckanext-scheming_dcat/commit/404b83887e35d817a9e4c806865fe0fb2032fae0) by mjanez).

### Removed

- Remove unnecessary static method decorator from normalize_string function ([8d7ab4b](https://github.com/mjanez/ckanext-scheming_dcat/commit/8d7ab4bfe9dab493bc55164c16f5eaa7de8bec25) by mjanez).

## [v4.2.2](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v4.2.2) - 2024-11-11

<small>[Compare with v4.2.1](https://github.com/mjanez/ckanext-scheming_dcat/compare/v4.2.1...v4.2.2)</small>

### Added

- Add text truncation styles for links, texts, and lists in metadata/resource info ([a48f239](https://github.com/mjanez/ckanext-scheming_dcat/commit/a48f23925ab131d0359156fbe13842e506da48a4) by mjanez).
- Add informational message for sysadmin users managing harvest sources and improve README ([6392811](https://github.com/mjanez/ckanext-scheming_dcat/commit/6392811c60f4758634340695562aa9c5004662eb) by mjanez).
- Add text truncation styles for dataset/resource metadata display ([e09c8c6](https://github.com/mjanez/ckanext-scheming_dcat/commit/e09c8c6664158441772d4f6d923d7c2df956a20d) by mjanez).

### Fixed

- Fix org label breadcrumb navigation ([ead4bfc](https://github.com/mjanez/ckanext-scheming_dcat/commit/ead4bfc79068d6a63a748bbe6bd8b6a9681f7795) by mjanez).
- Fix DCAT_AP_HVD_CATEGORY_LEGISLATION duplicates bug ([df062da](https://github.com/mjanez/ckanext-scheming_dcat/commit/df062da16832f6e81f8e56424c15f3e742c573ca) by mjanez).

## [v4.2.1](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v4.2.1) - 2024-11-04

<small>[Compare with v4.2.0](https://github.com/mjanez/ckanext-scheming_dcat/compare/v4.2.0...v4.2.1)</small>

### Added

- Add XLS_HARVESTER_FIELDS_NOT_LIST to exclude fields that are not lists XLS harvester list parser ([7c9e91f](https://github.com/mjanez/ckanext-scheming_dcat/commit/7c9e91f5fac88959810c3e2285a455c822e722fc) by mjanez).
- Add translations for "Parent" and "None - top level" in English and Spanish ([86e16a9](https://github.com/mjanez/ckanext-scheming_dcat/commit/86e16a941a189cc585f5f28d8d235f2f90c3e1e9) by mjanez).
- Add dataset_id_field to SchemingDCATXLSHarvester for identifier resolution of attached resources ([dcb88d3](https://github.com/mjanez/ckanext-scheming_dcat/commit/dcb88d301d4ba5f205a982bd4fec4ced5d182eef) by mjanez).
- Add BibTeX and RIS download functionality and enhance citation layout ([48b95c8](https://github.com/mjanez/ckanext-scheming_dcat/commit/48b95c85d04a87e7743220bd77c8e08820e34f5d) by mjanez).

### Fixed

- Fix data attributes for purge action (admin/trash.html) ([73311ba](https://github.com/mjanez/ckanext-scheming_dcat/commit/73311ba6f5be10e74acde1a5ca53e8f203cafb6b) by mjanez).
- Fix access_rights, maintainer and author field bugs ([ef1f26c](https://github.com/mjanez/ckanext-scheming_dcat/commit/ef1f26cdc7c9cdc1e3275214d6dda0522fa1d1b7) by mjanez).
- Fix dataset_id_field assignment in SchemingDCATXLSHarvester configuration ([1705773](https://github.com/mjanez/ckanext-scheming_dcat/commit/1705773a9a0e3e35b67f23eb3867bc0f95aa6e2b) by mjanez).
- Fix validators for dataset privacy settings (private) ([7b86e3c](https://github.com/mjanez/ckanext-scheming_dcat/commit/7b86e3cc02a0a4bf409a29ed49ff5930679ab44e) by mjanez).
- Fix dataset privacy settings logic and improve authorization messages ([b371495](https://github.com/mjanez/ckanext-scheming_dcat/commit/b3714956bddf26dd7943a97c199b75b8aa3646ab) by mjanez).
- Fix organization name retrieval to use display_name ([af8c4cc](https://github.com/mjanez/ckanext-scheming_dcat/commit/af8c4cc4093dacee4de09fef19ac52f0b803f7f7) by mjanez).

### Removed

- Removed old logic.py ([8de31b9](https://github.com/mjanez/ckanext-scheming_dcat/commit/8de31b94efc0602336cfb59952b28f82b7df13f0) by mjanez).

## [v4.2.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v4.2.0) - 2024-10-17

<small>[Compare with v4.1.0](https://github.com/mjanez/ckanext-scheming_dcat/compare/v4.1.0...v4.2.0)</small>

### Added

- Add Luxembourgish language support and remove duplicates in DCAT schemas ([294dcff](https://github.com/mjanez/ckanext-scheming_dcat/commit/294dcff015ce62728addd9a5554c2c45aa7855e4) by mjanez).
- Add dataset citation snippets and improve permanent URL handling ([0e22baf](https://github.com/mjanez/ckanext-scheming_dcat/commit/0e22baf41afc899a888d4428c660bc2e569d6975) by mjanez).

### Fixed

- Fix package update logging and event emission in SchemingDCATHarvester ([7ecb4fd](https://github.com/mjanez/ckanext-scheming_dcat/commit/7ecb4fd8ee1cdf5fadd9c33ba0cc87c2196ae517) by mjanez).

## [v4.1.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v4.1.0) - 2024-10-14

<small>[Compare with v4.0.0](https://github.com/mjanez/ckanext-scheming_dcat/compare/v4.0.0...v4.1.0)</small>

### Added

- Add number_size display snippet ([d05b4dd](https://github.com/mjanez/ckanext-scheming_dcat/commit/d05b4dddca562436720f51e99e18e0d4da304665) by mjanez).
- Add debug logging for full SQL query generation and remove unnecessary whitespace ([773c2fe](https://github.com/mjanez/ckanext-scheming_dcat/commit/773c2fefda50591110cff073757f947343394b29) by mjanez).
- Add Bootstrap class to title input in new source form template ([7a2dfd6](https://github.com/mjanez/ckanext-scheming_dcat/commit/7a2dfd639197b0a79e2075d205ce8cbe05c3201b) by mjanez).
- Add percentage and spatial resolution display snippets, and update spatial JSON rendering display/form snippets ([c47d62a](https://github.com/mjanez/ckanext-scheming_dcat/commit/c47d62a830b291b2163bdbff020b48cc86ddeaf1) by mjanez).
- Add initial implementation for SchemingDCAT logic and update actions ([a85808b](https://github.com/mjanez/ckanext-scheming_dcat/commit/a85808b638557cc3ce8636a76cceffb915bb5309) by mjanez).
- Add statistics logic and templates for SchemingDCAT integration ([e019582](https://github.com/mjanez/ckanext-scheming_dcat/commit/e019582622081f1ba1754c90d18cc8e2a9ab8d7d) by mjanez).
- Add signals for package updates and create statistics schema interface ([6bf0ba0](https://github.com/mjanez/ckanext-scheming_dcat/commit/6bf0ba011c8bdf87d239a71c0f2cc5a257519852) by mjanez).
- Add config_declaration CKAN >2.10 and refactor config.py to config/ ([4b8c741](https://github.com/mjanez/ckanext-scheming_dcat/commit/4b8c741e89bd0562aed8468e5fda9744fda6a048) by mjanez).
- Add config_declaration CKAN >2.10 ([aa49986](https://github.com/mjanez/ckanext-scheming_dcat/commit/aa49986c48fdab8cac6a4914ed3d359c7aa23fd6) by mjanez).

### Fixed

- Fix bug in SQL Harvester URL input help text in new source form ([c92fdb3](https://github.com/mjanez/ckanext-scheming_dcat/commit/c92fdb3c1348a4163416ee039d23874420dd56eb) by mjanez).
- Fix nested contact/author/maintainer/publisher fields ([f43eec2](https://github.com/mjanez/ckanext-scheming_dcat/commit/f43eec21e71a026cd6e110a5ba3baa68b2812dd0) by mjanez).
- Fix PostgreSQL database harvester description ([9661186](https://github.com/mjanez/ckanext-scheming_dcat/commit/9661186807527ce4cf208e701cd0336eca7a57aa) by mjanez).
- Fix request.params to request.args ([eda46f8](https://github.com/mjanez/ckanext-scheming_dcat/commit/eda46f83b8292f61dde80a6266e93bd5674d7ec8) by mjanez).
- Fix current_url assignment in schemingdcat_social.html ([c45eaca](https://github.com/mjanez/ckanext-scheming_dcat/commit/c45eaca3e93c38f8ea10420c61448ae373f534b6) by mjanez).
- Fix es_dcat PeriodOfTime class if not exists temporal_* ([f3873ea](https://github.com/mjanez/ckanext-scheming_dcat/commit/f3873ea0ccdbe40fb30a8447b554f5eab06e87c2) by mjanez).
- FIx harvest source form ([98ccd3c](https://github.com/mjanez/ckanext-scheming_dcat/commit/98ccd3c537dbee46cf96e4d954ab2a4709a93e48) by mjanez).

## [v4.0.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v4.0.0) - 2024-09-20

<small>[Compare with v4.0.0-alpha](https://github.com/mjanez/ckanext-scheming_dcat/compare/v4.0.0-alpha...v4.0.0)</small>

### Added

- Add highlighting and quote alerts ([eefdcac](https://github.com/mjanez/ckanext-scheming_dcat/commit/eefdcac72b3f4856844b2cfef7b783f3b9b63010) by mjanez).

### Fixed

- Fix api button accordions ([fcec54b](https://github.com/mjanez/ckanext-scheming_dcat/commit/fcec54bd4c41cf0c2e61cebcce17ea420465501c) by mjanez).

## [v4.0.0-alpha](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v4.0.0-alpha) - 2024-09-20

<small>[Compare with v3.2.1](https://github.com/mjanez/ckanext-scheming_dcat/compare/v3.2.1...v4.0.0-alpha)</small>

### Added

- Add xls_template_config ([69e04f3](https://github.com/mjanez/ckanext-scheming_dcat/commit/69e04f363858b67331ab6b9617fe03135c0eb72d) by mjanez).
- Add docs and templates for harvesters ([e136909](https://github.com/mjanez/ckanext-scheming_dcat/commit/e1369092b8fcf750c9c8a399a93086b2faf81232) by mjanez).
- Add docker-compose tests ([9b16a8f](https://github.com/mjanez/ckanext-scheming_dcat/commit/9b16a8f879736012842f8057454fc86e959a0469) by mjanez).
- Add conftest.py for testing with clean database ([5c183ac](https://github.com/mjanez/ckanext-scheming_dcat/commit/5c183ac8c5946d0203568e9a32a703d97a185ea8) by mjanez).
- Add codelists for DCAT profiles ([ff4de2c](https://github.com/mjanez/ckanext-scheming_dcat/commit/ff4de2c614585cfffdc52814944188bc8ae20c59) by mjanez).
- Add reference and representation_type ([2184aad](https://github.com/mjanez/ckanext-scheming_dcat/commit/2184aad8168e175cdeaa8fc1dff9247cc26c5567) by mjanez).
- Add deprecated decorator to mark functions as deprecated ([e1e488c](https://github.com/mjanez/ckanext-scheming_dcat/commit/e1e488c5e124398ac9d82384b22b981712f8d1c8) by mjanez).
- Add SHACL tests for custom profiles ([8f0e6f3](https://github.com/mjanez/ckanext-scheming_dcat/commit/8f0e6f3522bddc90beb6c931111a8a0279b646ea) by mjanez).
- Add ckanext-dcat custom profiles ([d949571](https://github.com/mjanez/ckanext-scheming_dcat/commit/d949571e1fc49e71d82e2e00f40a5535286ff815) by mjanez).
- Add form tabs to dataset creation/editing datasets/resources ([2da1c1f](https://github.com/mjanez/ckanext-scheming_dcat/commit/2da1c1f828dd48ad274fe0b85ae4e9e4958e2ebb) by mjanez).
- Add licenses.json ([ea133a3](https://github.com/mjanez/ckanext-scheming_dcat/commit/ea133a3ee40a574744c070db871f7d27b257f8c5) by mjanez).
- Add form tabs to schemas and templates ([bab7d58](https://github.com/mjanez/ckanext-scheming_dcat/commit/bab7d58375ae35c86dc2f5611fa34b6d2b477504) by mjanez).
- Add schemingdcat_get_choice_property helper ([b4ec09e](https://github.com/mjanez/ckanext-scheming_dcat/commit/b4ec09e5f4cdf667e3175b93b8d6e162db308b26) by mjanez).

### Fixed

- Fix xloader logs styles for 2.10 ([bac0862](https://github.com/mjanez/ckanext-scheming_dcat/commit/bac0862dbf3c15d076725c1c392ababdbe3bed89) by mjanez).
- Fix tags containers ([50945d0](https://github.com/mjanez/ckanext-scheming_dcat/commit/50945d0fd9fb1c3d101c90cc5b9a46f1034a5e5d) by mjanez).
- Fix spatial_query snippet bugs ([3026467](https://github.com/mjanez/ckanext-scheming_dcat/commit/30264674345c1aa077f5f2e1546e3fd0834f0eb8) by mjanez).
- Fix organization create/edit button bugs ([4b10208](https://github.com/mjanez/ckanext-scheming_dcat/commit/4b1020840974b3419358c473a151aa3294d8ae6d) by mjanez).
- Fix package snippets ([448113e](https://github.com/mjanez/ckanext-scheming_dcat/commit/448113effa71867fc00671375e780dd4b29c78ff) by mjanez).
- Fix Solr indexing by converting dict fields to JSON strings ([fb8abf6](https://github.com/mjanez/ckanext-scheming_dcat/commit/fb8abf6ac5aed3bd6c7e054c6c09bf380417f944) by mjanez).
- Fix tabs slug-preview and dataset-map ([1af58e1](https://github.com/mjanez/ckanext-scheming_dcat/commit/1af58e16088cf2565f9c95f6a244615a110ce1f5) by mjanez).
- Fix before_update ([7c303d9](https://github.com/mjanez/ckanext-scheming_dcat/commit/7c303d907542fc9b22f568187ce3f51b20a0f2b3) by mjanez).
- Fix fa icons for license/social templates ([f358203](https://github.com/mjanez/ckanext-scheming_dcat/commit/f358203b2f0220d14734b8ea9da85092adbe6e79) by mjanez).
- Fix and improve templates for CKAN 2.10 ([c7aabef](https://github.com/mjanez/ckanext-scheming_dcat/commit/c7aabeffa795f77e35211ca0e6e50cde0996851b) by mjanez).
- Fix search and index to ensure proper functionality ([c294495](https://github.com/mjanez/ckanext-scheming_dcat/commit/c294495c9ee3e45c6a05789a0360939eeb16da67) by mjanez).
- FIx templates with new profiles ([dcd144e](https://github.com/mjanez/ckanext-scheming_dcat/commit/dcd144ea64026f53be1d91bc7088177d4845cbc3) by mjanez).
- Fix eu_dcat_ap profile ([75a45bd](https://github.com/mjanez/ckanext-scheming_dcat/commit/75a45bd5725c249eb77cda8175575b2b19addbc4) by mjanez).
- Fix rights bug ([0b2d0cc](https://github.com/mjanez/ckanext-scheming_dcat/commit/0b2d0cc068b01653c5f243de6cf6f1bd37c6b4e8) by mjanez).
- FIx shacl file path to include version subdir ([2b4ddad](https://github.com/mjanez/ckanext-scheming_dcat/commit/2b4ddad0fc779e78511f69c8fca8531ebe22af09) by mjanez).
- FIx test_shacl & update example ckan datasets ([af0710a](https://github.com/mjanez/ckanext-scheming_dcat/commit/af0710a6e81465c7df49adfaef2f5974f2a4aecf) by mjanez).
- Fix test_shacl ([3ff0417](https://github.com/mjanez/ckanext-scheming_dcat/commit/3ff04177074350b2423a72cd53c7ff40c19dd045) by mjanez).
- Fix test error, add harvest to plugins ([5091c67](https://github.com/mjanez/ckanext-scheming_dcat/commit/5091c679d4c18ef94abc9e5def8f3fbf700a9cc3) by mjanez).
- Fix F821 undefined name ([bb9f4fd](https://github.com/mjanez/ckanext-scheming_dcat/commit/bb9f4fd55f5453ce3a4b5aba4e7f2254785c5fa4) by mjanez).
- Fix file_size in resource metadata info ([2128d6c](https://github.com/mjanez/ckanext-scheming_dcat/commit/2128d6cc174ecbac28b650f6f7a96cb0ffc9a279) by mjanez).
- Fix translated_fields generation ([49c4d24](https://github.com/mjanez/ckanext-scheming_dcat/commit/49c4d247cc4883f79aca81859e7344e8dde43a72) by mjanez).
- Fix CKAN harvester search functionality ([3952322](https://github.com/mjanez/ckanext-scheming_dcat/commit/3952322c036b7eeb4d3b2407448c943a842cf521) by mjanez).
- Fix bug when schemingdcat.endpoints_yaml is None ([36a298e](https://github.com/mjanez/ckanext-scheming_dcat/commit/36a298e9b3f2671c477dbf02da6280d61284aa07) by mjanez).
- Fix schemas README link ([bee583e](https://github.com/mjanez/ckanext-scheming_dcat/commit/bee583e0ead01b31f9be3cfb79631283869a722f) by mjanez).
- Fix search box width ([2abe18e](https://github.com/mjanez/ckanext-scheming_dcat/commit/2abe18e0ac73c376ad2aab777e961d7e5a5b4365) by mjanez).
- Fix search box in datasets/orgs/groups ([a5a58e2](https://github.com/mjanez/ckanext-scheming_dcat/commit/a5a58e2448886343be8ebf0f54fdee66b3d61f95) by mjanez).

### Removed

- Removed unnecessary data-bs attributes for custom slug-preview module ([ddc4de6](https://github.com/mjanez/ckanext-scheming_dcat/commit/ddc4de62efba03803d4550769482bbb7ace5a11e) by mjanez).

## [v3.2.1](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v3.2.1) - 2024-07-10

<small>[Compare with v3.2.1-alpha](https://github.com/mjanez/ckanext-scheming_dcat/compare/v3.2.1-alpha...v3.2.1)</small>

### Fixed

- Fix problem with defaults_values from config ([ea02b53](https://github.com/mjanez/ckanext-scheming_dcat/commit/ea02b530dc2cc48eae9620204a7eec14184114b5) by mjanez).
- Fix resource mimetype update ([3217e8d](https://github.com/mjanez/ckanext-scheming_dcat/commit/3217e8d9db5cff46d930a229e93db17fa18c88dd) by mjanez).

## [v3.2.1-alpha](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v3.2.1-alpha) - 2024-06-27

<small>[Compare with first commit](https://github.com/mjanez/ckanext-scheming_dcat/compare/a64993ad67b965a189677806b3f3588ed7b20fc1...v3.2.1-alpha)</small>

### Added

- Add admin/config template i18n ([c58f697](https://github.com/mjanez/ckanext-scheming_dcat/commit/c58f697f4d998cd23356f6305f8cf3e8deb6aa30) by mjanez).
- Add schemingdcat_xls harvester template ([3b118b2](https://github.com/mjanez/ckanext-scheming_dcat/commit/3b118b2624805962cd847fcb0af842adc9a3df20) by mjanez).
- Add info to schemingdcat_ows harvester ([e19957c](https://github.com/mjanez/ckanext-scheming_dcat/commit/e19957c8596541ee14454ca41eac157c832bc3d6) by mjanez).

### Fixed

- Fix endpoints template when sparql_interface is not active ([a608ad2](https://github.com/mjanez/ckanext-scheming_dcat/commit/a608ad28a40beea622b3fe025fe7fba4e8f73735) by mjanez).
- Fix translation issue in schemingdcat_facet_list template ([9e91862](https://github.com/mjanez/ckanext-scheming_dcat/commit/9e918622d6ff91d29532bfe8f2fe783007b52f1c) by mjanez).

## [v3.2.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v3.2.0) - 2024-06-17

<small>[Compare with v3.1.0](https://github.com/mjanez/ckanext-scheming_dcat/compare/v3.1.0...v3.2.0)</small>

### Added

- Adding metadata template logic and theming ([1acfab4](https://github.com/mjanez/ckanext-scheming_dcat/commit/1acfab4a02e91be62bc11cfb3b3b5e884e72e618) by mjanez).
- Add metatata templates sidebar for schemingdcat_xls harvester ([f01c058](https://github.com/mjanez/ckanext-scheming_dcat/commit/f01c058843f864304e437ad690ba3e836ea248ee) by mjanez).
- Add display snippet for spatial JSON in default presets ([cb8da30](https://github.com/mjanez/ckanext-scheming_dcat/commit/cb8da30ec8aa87250e9880dc7d52dd15775064e6) by mjanez).
- Add custom format validator ([7ec5510](https://github.com/mjanez/ckanext-scheming_dcat/commit/7ec5510ae375ea8db4bc032f9ae88d604cb1546d) by mjanez).
- Add EU to spatial_uri ([e92c96c](https://github.com/mjanez/ckanext-scheming_dcat/commit/e92c96cd76270dfd86aa7e14995f3fbf0e410692) by mjanez).
- Add css for distribution formats ([b16bece](https://github.com/mjanez/ckanext-scheming_dcat/commit/b16becee7f56aba6e24738e5e2b76bcfa0880b77) by mjanez).
- Add temporal_start and temporal_end fields to DATE_FIELDS ([f37bb45](https://github.com/mjanez/ckanext-scheming_dcat/commit/f37bb45dcf7988021bb3e84511b7ca211c98480e) by mjanez).
- Add data-icons for provincias and provincias images based on autonomies ([7ce296d](https://github.com/mjanez/ckanext-scheming_dcat/commit/7ce296df13bb4df6c3a481c755348569f5120a6c) by mjanez).
- Add schemingdcat_spatial_uri_validator to obtain spatial from spatial_uri ([522415c](https://github.com/mjanez/ckanext-scheming_dcat/commit/522415c364a955581289069ad5410bf2618f127f) by mjanez).

### Fixed

- Fix list elements ([91189db](https://github.com/mjanez/ckanext-scheming_dcat/commit/91189dbc95cb24ec6665dd7e21eb529e5a19416c) by mjanez).
- Fix ZIP format color ([056e3a4](https://github.com/mjanez/ckanext-scheming_dcat/commit/056e3a4076efa22b25f73fe9773a3d622c46837d) by mjanez).
- Fix local_schema in import_stage ([c62daba](https://github.com/mjanez/ckanext-scheming_dcat/commit/c62daba4912523996a51105401e1cc235fd8ec19) by mjanez).
- Fix spaces between warnings in metadata-templates ([9dde146](https://github.com/mjanez/ckanext-scheming_dcat/commit/9dde146d9ab6f6571baea89b5475dbd3f85f0512) by mjanez).
- Fix contact/publisher info snippets to avoid errors with emails ([5271ed9](https://github.com/mjanez/ckanext-scheming_dcat/commit/5271ed9ec6c6eed85124c6c70ba1d50531f10d69) by mjanez).
- Fix icon class for university publisher type ([30b3e35](https://github.com/mjanez/ckanext-scheming_dcat/commit/30b3e35eca48f52c824b0034b54a49982a7d7eda) by mjanez).
- Fix contact_info and publisher_info snippets ([661b431](https://github.com/mjanez/ckanext-scheming_dcat/commit/661b4316e70052cf9e7fce71300f3ad3d901a052) by mjanez).
- Fix stages css ([3d2069a](https://github.com/mjanez/ckanext-scheming_dcat/commit/3d2069a3328e8f9a95acbc846975332da8e67fac) by mjanez).
- Fix schemingdcat_prettify_url_name ([288f75f](https://github.com/mjanez/ckanext-scheming_dcat/commit/288f75f206b02e3e0acdbbb7349f1c42462d31df) by mjanez).
- Fix org form_placeholder ([d4ff46c](https://github.com/mjanez/ckanext-scheming_dcat/commit/d4ff46cc2e6005b1c4446b177e92c1b6f5fc9e78) by mjanez).
- Fix badges ([490e65f](https://github.com/mjanez/ckanext-scheming_dcat/commit/490e65f496b389b95bb470f1e003cf85e9a78250) by mjanez).
- Fix flags from spatial_uri in contac_info snippet ([c2c9bcd](https://github.com/mjanez/ckanext-scheming_dcat/commit/c2c9bcd6b03bae5b3e7616e8fe816cfd5a62a9f6) by mjanez).
- Fix dataset-categories icons position ([0b81573](https://github.com/mjanez/ckanext-scheming_dcat/commit/0b8157358e0ae90c8e736af1d3e6d64b5827fa27) by mjanez).

### Removed

- Remove logs ([f9fbccd](https://github.com/mjanez/ckanext-scheming_dcat/commit/f9fbccdc64b1e206e6350df9d405064e553c8eed) by mjanez).

## [v3.1.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v3.1.0) - 2024-05-28

<small>[Compare with v3.0.0](https://github.com/mjanez/ckanext-scheming_dcat/compare/v3.0.0...v3.1.0)</small>

### Added

- Add icons to package items to render theme/spatial_uri ([fcd7bbe](https://github.com/mjanez/ckanext-scheming_dcat/commit/fcd7bbe09b2eacf7bee4dbec922a2793cc7c5d4c) by mjanez).
- Add non_spatial_dataset field ([b455bc6](https://github.com/mjanez/ckanext-scheming_dcat/commit/b455bc6386e655ec0b7a53e99995607b47443536) by mjanez).
- Add endpoint index to endpoints layout ([2beff9d](https://github.com/mjanez/ckanext-scheming_dcat/commit/2beff9df99778ed80edf285de5d07f66d85a2ffd) by mjanez).
- Add /endpoints blueprint ([ebba116](https://github.com/mjanez/ckanext-scheming_dcat/commit/ebba116b0021c5b5987ec07982c812f755bf1e98) by mjanez).
- Add get_ckan_cleaned_name helper ([133a40c](https://github.com/mjanez/ckanext-scheming_dcat/commit/133a40c156179db17896f5372c0ebc07ddb5b0e3) by mjanez).
- Add theme_es, theme, theme_eu, topic and hvd_category to translations ([a76873e](https://github.com/mjanez/ckanext-scheming_dcat/commit/a76873e129bb7661f96fe07cf58938ec025ed6c1) by mjanez).
- Add commands to create tags based on schema themes and topics ([0f75976](https://github.com/mjanez/ckanext-scheming_dcat/commit/0f7597638e91e5d1599e6b79c2cc4d953f188cc4) by mjanez).
- Add multiple_choice_custom_tag preset ([050d157](https://github.com/mjanez/ckanext-scheming_dcat/commit/050d157c39a350ce24863570ebe119841c4f13f9) by mjanez).
- Add YAML file and script for generating translation files ([01fc225](https://github.com/mjanez/ckanext-scheming_dcat/commit/01fc225f3953602aa025859a739057e81f04edee) by mjanez).
- Add debug info to header in dev mode ([a053b43](https://github.com/mjanez/ckanext-scheming_dcat/commit/a053b43f70bb684241a94ca325a15b1100fab3b2) by mjanez).
- Add hvd_category to metadata_info template ([e79209a](https://github.com/mjanez/ckanext-scheming_dcat/commit/e79209a60b7c991cfe67969af0c8ce9418fe698e) by mjanez).
- Add select_spatial_icon preset for geographic identifier field ([332ceec](https://github.com/mjanez/ckanext-scheming_dcat/commit/332ceec0db82859357995e5c4dce8dc1f1135bb7) by mjanez).
- Add high-value dataset category field ([cf42f5b](https://github.com/mjanez/ckanext-scheming_dcat/commit/cf42f5bba6863432697222f6ab96e3a1f194252a) by mjanez).

### Fixed

- Fix theme_es classes ([083e500](https://github.com/mjanez/ckanext-scheming_dcat/commit/083e50078ffa5d1dd25421d2e7a8d8e25a975153) by mjanez).
- FIx generate_translation_files ([cb1ff4d](https://github.com/mjanez/ckanext-scheming_dcat/commit/cb1ff4df293719593d83b0718ad08b1f48f91199) by mjanez).

## [v3.0.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v3.0.0) - 2024-04-27

<small>[Compare with v2.1.0](https://github.com/mjanez/ckanext-scheming_dcat/compare/v2.1.0...v3.0.0)</small>

### Fixed

- Fix ckan harvester issues ([93da11a](https://github.com/mjanez/ckanext-scheming_dcat/commit/93da11a97b3a5ed55c586a63ad76a8986d47b1a7) by mjanez).
- Fix resource/dataset update when use XLS Harvester ([b1117c0](https://github.com/mjanez/ckanext-scheming_dcat/commit/b1117c0d110deca3ff8de1ec042245d024e17106) by mjanez).
- Fix accented character handling in SchemingDCATHarvester ([9074fed](https://github.com/mjanez/ckanext-scheming_dcat/commit/9074fed29aa1bfacbb57404460cc0a840947c081) by mjanez).
- Fix source_date_format issue in SchemingDCATHarvester ([0fca9da](https://github.com/mjanez/ckanext-scheming_dcat/commit/0fca9da26533ec204dfa5c8800cc259fbc7ff01b) by mjanez).
- Fix resource updating for XLS harvester ([35e1371](https://github.com/mjanez/ckanext-scheming_dcat/commit/35e137196c46eed44a4287f84415066b3148b3c6) by mjanez).
- Fix old scheming_dcat prefix and adapt helpers from harvest ([54b9833](https://github.com/mjanez/ckanext-scheming_dcat/commit/54b9833a91c1944b3994d397a0b7fc385dfca682) by mjanez).
- Fix bugs ckan harvester ([b309e1a](https://github.com/mjanez/ckanext-scheming_dcat/commit/b309e1ab776af5f4591642b5d28d4aaf87ebb802) by mjanez).
- Fix extras instance in SchemingDCATHarvester ([560863c](https://github.com/mjanez/ckanext-scheming_dcat/commit/560863cd68614871bab83d4bc88b27f8cb75a13f) by mjanez).
- Fix map attribution acording to ckanext-spatial ([b8782c6](https://github.com/mjanez/ckanext-scheming_dcat/commit/b8782c60eb1110efdeee33c0e77b6e8eb506c95c) by mjanez).
- Fix all to schemingdcat ([1cf8bfb](https://github.com/mjanez/ckanext-scheming_dcat/commit/1cf8bfbb7ac91e0ab012fad4f73f8aca833b68c8) by mnjnz).
- Fix scheming_dcat name to schemingdcat (PEP 503 y PEP 508) ([7f30286](https://github.com/mjanez/ckanext-scheming_dcat/commit/7f30286d8b26bbe8c5ba675725823a6eaaffa261) by mjanez).

### Removed

- Remove duplicate LICENSE.txt ([e6d2c22](https://github.com/mjanez/ckanext-scheming_dcat/commit/e6d2c22a8a97ebbbeb58334bb829b33b815789fe) by mjanez).
- Remove log.debug ([6f49461](https://github.com/mjanez/ckanext-scheming_dcat/commit/6f494612eb211d9431c682787e6a45021ac9bc9a) by mjanez).

## [v2.1.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v2.1.0) - 2024-03-11

<small>[Compare with v2.0.0](https://github.com/mjanez/ckanext-scheming_dcat/compare/v2.0.0...v2.1.0)</small>

### Added

- Add default values to package_dict ([ed746d1](https://github.com/mjanez/ckanext-scheming_dcat/commit/ed746d121ad680a758c21d42c95aafdf57d0ef8c) by mjanez).
- Add gspread auth storage_type ([b7c3957](https://github.com/mjanez/ckanext-scheming_dcat/commit/b7c3957db9530a2f14502b81bfcf7463b8b0e127) by mjanez).
- Add new XLS Harvester ([81f32ad](https://github.com/mjanez/ckanext-scheming_dcat/commit/81f32adfbc3487b8a2582d456a8b9fe5f28144f2) by mjanez).
- Add scheming_dcat harvester plugins ([42bfafc](https://github.com/mjanez/ckanext-scheming_dcat/commit/42bfafc2df10286a3dc6d12d8a1d8ad55545db4e) by mjanez).

### Fixed

- Fix groups ingest ([9f5c6c3](https://github.com/mjanez/ckanext-scheming_dcat/commit/9f5c6c375338e32d13dd7d529584e0a2a03c21b1) by mjanez).
- Fix codelists folder ([128aa5c](https://github.com/mjanez/ckanext-scheming_dcat/commit/128aa5c413207b152677671f04eb97b7cb9691ed) by mjanez).
- Fix csw harvester WIP ([095acfe](https://github.com/mjanez/ckanext-scheming_dcat/commit/095acfe58c8a9352accc8ea556f55b7dbe296b79) by mjanez).
- Fix group items templates in dataset ([eddee38](https://github.com/mjanez/ckanext-scheming_dcat/commit/eddee380c9749cf2ff252f3e029af1c0dbe88bdf) by mjanez).

## [v2.0.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v2.0.0) - 2023-10-20

<small>[Compare with v1.2.0](https://github.com/mjanez/ckanext-scheming_dcat/compare/v1.2.0...v2.0.0)</small>

### Added

- Add multilang to groups and organisations ([c046561](https://github.com/mjanez/ckanext-scheming_dcat/commit/c046561259213ce9e91b0ed2615e1d29ef3aeb44) by mjanez).
- Add multilang to search templates ([5ab6bfd](https://github.com/mjanez/ckanext-scheming_dcat/commit/5ab6bfd7b0a3d5df3bb9cc92fbd83a8e6dc2370d) by mjanez).
- Add multilang promoted home text (intro_text) ([3ebec32](https://github.com/mjanez/ckanext-scheming_dcat/commit/3ebec32a74679541c822c97c14e37e869f57cf47) by mjanez).
- Add modern theme to CKAN and CSW/LOD endpoints at home ([26114c1](https://github.com/mjanez/ckanext-scheming_dcat/commit/26114c1912a92b5e1a7ed24e846e75d85b6c4041) by mjanez).

### Fixed

- Fix scheming_dct_get_localised_value_from_dict to allow use of untranslated field ([253c637](https://github.com/mjanez/ckanext-scheming_dcat/commit/253c6373d74096e23a871d0c17668ba121ce7280) by mjanez).
- Fix default lang, prefer schema required and then locale_default ([45fd50b](https://github.com/mjanez/ckanext-scheming_dcat/commit/45fd50b5ef47e171ca5720186aa830ac2216af32) by mjanez).
- Fix multilang display and core fields validator ([e03c38c](https://github.com/mjanez/ckanext-scheming_dcat/commit/e03c38cc5161bb8b2763bc1ce75085f855a935d8) by mjanez).
- Fix ckanext-fluent with custom extensions ([0b6e9b8](https://github.com/mjanez/ckanext-scheming_dcat/commit/0b6e9b8d088cab604a9fe80e11d6ab2751f36300) by mjanez).
- Fix schemingdct_prettify_url_name ([3894ded](https://github.com/mjanez/ckanext-scheming_dcat/commit/3894ded883d62c05de4c5e10615dbf5e8b727f38) by mjanez).
- Fix schemingdct_prettify_url_name to avoid Nones ([2353f61](https://github.com/mjanez/ckanext-scheming_dcat/commit/2353f616a898a04817bd46b9ac0c6c5dc599632d) by mjanez).
- Fix header logo and footer ([6e13958](https://github.com/mjanez/ckanext-scheming_dcat/commit/6e13958759132fc7cc377896f01363b9ee859782) by mjanez).
- Fix sd_config.endpoints ([3f8a89f](https://github.com/mjanez/ckanext-scheming_dcat/commit/3f8a89f88938710c71db54a297d44e7ca6c3dce4) by mjanez).

## [v1.2.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v1.2.0) - 2023-09-06

<small>[Compare with v1.1.0](https://github.com/mjanez/ckanext-scheming_dcat/compare/v1.1.0...v1.2.0)</small>

### Added

- add purpose metadata element to GeoDCAT-AP Schemas ([d283a14](https://github.com/mjanez/ckanext-scheming_dcat/commit/d283a143c1140968bbb85567c28692fc48d337d5) by mjanez).
- Add new packages read templates ([f77250b](https://github.com/mjanez/ckanext-scheming_dcat/commit/f77250baf9385c28a408bff3a915a159f6fe7175) by mjanez).
- Add Js assets ([2537057](https://github.com/mjanez/ckanext-scheming_dcat/commit/25370571cf177f16d14fda64b1cca0e5ce26f495) by mjanez).
- Add theme_es to schemingdct_info if exists ([d05afc9](https://github.com/mjanez/ckanext-scheming_dcat/commit/d05afc95e1fa8117dcaeb9ce0d70719ddbc8189a) by mjanez).
- Add spatial_uri for EU Context ([dac2a14](https://github.com/mjanez/ckanext-scheming_dcat/commit/dac2a14f22452d8dfb2d10c9f95a76a92424ba75) by mjanez).
- Add schemas info to README ([6b13b61](https://github.com/mjanez/ckanext-scheming_dcat/commit/6b13b618fb2b70b7f05f575abecbf13dc48c31ff) by mjanez).
- Add dcat base schema ([9a9e648](https://github.com/mjanez/ckanext-scheming_dcat/commit/9a9e6485ba2457168209cd771e0c43165c57666e) by mjanez).

### Fixed

- Fix yaml error ([38ecc47](https://github.com/mjanez/ckanext-scheming_dcat/commit/38ecc47c7cecb8fc17d7ed8bdd4f67cdac0c92f2) by mjanez).
- Fix resourcedictionary in package_resource template ([51540f2](https://github.com/mjanez/ckanext-scheming_dcat/commit/51540f26a60dee4f3615297da1c619ee5e3a8763) by mjanez).
- Fix org bulk_process template ([035bca6](https://github.com/mjanez/ckanext-scheming_dcat/commit/035bca65d32a4f9a49fc557d70f7d19976d0dadb) by mjanez).
- Fix snippets ([4292ee1](https://github.com/mjanez/ckanext-scheming_dcat/commit/4292ee14f7bcc8dd8eecb7b8ccde8bc154467c07) by mjanez).
- Fix custom_data snippets ([a2e900c](https://github.com/mjanez/ckanext-scheming_dcat/commit/a2e900cc741eb864ab2e34ed89e0b5614cfb6596) by mjanez).
- Fix resource_read with extra fields ([be8b038](https://github.com/mjanez/ckanext-scheming_dcat/commit/be8b0387aafe4d6a4b0707600657b955226c50d0) by mjanez).
- Fix info snippet from package ([d9458bc](https://github.com/mjanez/ckanext-scheming_dcat/commit/d9458bc577a14bdf573134cae12fb0afa751f4c4) by mjanez).
- Fix resource_read ([b0efb43](https://github.com/mjanez/ckanext-scheming_dcat/commit/b0efb4379cbbfadd94f7dbeb432c9babf87aa6f2) by mjanez).
- Fix data_access_license block ([d06a864](https://github.com/mjanez/ckanext-scheming_dcat/commit/d06a8647c317de3981619666031f8cd4d15b0243) by mjanez).
- Fix read_base secondary items ([948a180](https://github.com/mjanez/ckanext-scheming_dcat/commit/948a1803393882acc4057e59140a099e0f35df5c) by mjanez).
- Fix ckan helper deprecated ([dd17e48](https://github.com/mjanez/ckanext-scheming_dcat/commit/dd17e482d8c98dfffe170f0d16ab40398b015922) by mjanez).
- Fix data_access_license if not access_rights ([87274bf](https://github.com/mjanez/ckanext-scheming_dcat/commit/87274bf83cf616623239aa90f50ab7854ac8a9c3) by mjanez).
- Fix image org css (schemingdct_info) ([8d0840a](https://github.com/mjanez/ckanext-scheming_dcat/commit/8d0840acb4251477694fb4c323ea79e3e1c63969) by mjanez).
- Fix data_access_license template ([7730310](https://github.com/mjanez/ckanext-scheming_dcat/commit/7730310cdcfdafacc708f6d581f805d35ade4447) by mjanez).
- Fix translation ([0cca67f](https://github.com/mjanez/ckanext-scheming_dcat/commit/0cca67f712f9138499626d9348458f6f073098c5) by mjanez).
- Fix spatial_query translates ([38724ce](https://github.com/mjanez/ckanext-scheming_dcat/commit/38724cee26dfdb264c3b99b766523bd9cd5cad20) by mjanez).
- Fix setup/plugin.py ([8945eab](https://github.com/mjanez/ckanext-scheming_dcat/commit/8945eabdaf9903902a7e2fd6558d243f3f1d7e51) by mjanez).
- Fix README ([103d5d5](https://github.com/mjanez/ckanext-scheming_dcat/commit/103d5d5adca8a067c80fc1679f847553718d4a29) by mjanez).
- Fix GeoDCAT-AP Schema and add geodcatap_es base ([26252ea](https://github.com/mjanez/ckanext-scheming_dcat/commit/26252eaf4182fc7f19ffdde73330d1befebd5aa7) by mjanez).

### Removed

- Remove debug in table-collapsible-rows module ([7807771](https://github.com/mjanez/ckanext-scheming_dcat/commit/7807771021bfc7f9bee790999cb0baf1c42350d5) by mjanez).

## [v1.1.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v1.1.0) - 2023-08-22

<small>[Compare with v1.0.0](https://github.com/mjanez/ckanext-scheming_dcat/compare/v1.0.0...v1.1.0)</small>

### Fixed

- Fix package/read_base.html ([c8f02aa](https://github.com/mjanez/ckanext-scheming_dcat/commit/c8f02aa0207973f73fd9b9a9c996de30e4eedae8) by mjanez).
- Fix geodcatap schema ([a61ceca](https://github.com/mjanez/ckanext-scheming_dcat/commit/a61ceca0fba3fa9503343b921cebbdc10187db88) by mjanez).
- Fix py files ([c00a8e4](https://github.com/mjanez/ckanext-scheming_dcat/commit/c00a8e4e1ac7890388b89e816dedeb8d2e75f855) by mjanez).

## [v1.0.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/v1.0.0) - 2023-08-16

<small>[Compare with 1.0.1](https://github.com/mjanez/ckanext-scheming_dcat/compare/1.0.1...v1.0.0)</small>

### Fixed

- Fix spatial_uri hrefs & icon render ([9d7867c](https://github.com/mjanez/ckanext-scheming_dcat/commit/9d7867ce8693e3250a3882bffebe67d1a17fc2e7) by mjanez).
- Fix doc ([9dd6d7f](https://github.com/mjanez/ckanext-scheming_dcat/commit/9dd6d7f0f313ba2b89c8a120d4fc2174ece96e3e) by mjanez).
- Fix filenames ([c863c7e](https://github.com/mjanez/ckanext-scheming_dcat/commit/c863c7ef9283c1e678dbb48ad71ac0f4d681bf2a) by mjanez).
- Fix README ([775a2ce](https://github.com/mjanez/ckanext-scheming_dcat/commit/775a2ce42243c4fb718224dfe04870b28a98496f) by mjanez).
- Fix setup and i18n ([efa5b75](https://github.com/mjanez/ckanext-scheming_dcat/commit/efa5b75df0f89da91522a8dc03366212145e154f) by mjanez).
- Fix geodcatap schema ([42d64af](https://github.com/mjanez/ckanext-scheming_dcat/commit/42d64af7937ec4a3923c7b72b1075d62bfaf360f) by mjanez).

## [1.0.1](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/1.0.1) - 2023-07-03

<small>[Compare with 1.0.0](https://github.com/mjanez/ckanext-scheming_dcat/compare/1.0.0...1.0.1)</small>

### Fixed

- Fix spatial_uri hrefs & icon render ([ad263de](https://github.com/mjanez/ckanext-scheming_dcat/commit/ad263de3b3dbef98986af1a707b4bd9d2f13ee40) by mjanez).

## [1.0.0](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/1.0.0) - 2023-05-06

<small>[Compare with 0.0.1](https://github.com/mjanez/ckanext-scheming_dcat/compare/0.0.1...1.0.0)</small>

### Fixed

- Fix .gitignore files ([6d773c0](https://github.com/mjanez/ckanext-scheming_dcat/commit/6d773c08ce8d67efbf085999415b808f86bd090e) by mjanez).
- Fix errors ([d768ce1](https://github.com/mjanez/ckanext-scheming_dcat/commit/d768ce1431d6a75a103714bfa82d90cc037cbe0e) by mnjnz).
- Fix setup.py to facet_scheming ([8dc719c](https://github.com/mjanez/ckanext-scheming_dcat/commit/8dc719c1e49e11f76ab63ca0401204b04c826331) by mnjnz).
- Fix 2 ([6be368a](https://github.com/mjanez/ckanext-scheming_dcat/commit/6be368a7004c5d58a5ab12d5025d8409a2451977) by mnjnz).
- Fix #1 ([1dfd51e](https://github.com/mjanez/ckanext-scheming_dcat/commit/1dfd51efc125ada1464e3eed86f5f1f24b379062) by mnjnz).
- Fix extension name & update README ([cf855ad](https://github.com/mjanez/ckanext-scheming_dcat/commit/cf855adceb8691163e82c6938ba656330db5ae44) by mjanez).

## [0.0.1](https://github.com/mjanez/ckanext-scheming_dcat/releases/tag/0.0.1) - 2023-04-28

<small>[Compare with first commit](https://github.com/mjanez/ckanext-scheming_dcat/compare/435f7d6d5f20fa719be814ddf8d67edb03bd7bf3...0.0.1)</small>

