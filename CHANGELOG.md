# CHANGELOG

<!-- version list -->

## v1.9.0 (2026-02-18)

### Bug Fixes

- **cli**: Mock git_init in existing scaffold pipeline test
  ([#28](https://github.com/michaelellis003/uv-python-template/pull/28),
  [`e05cd19`](https://github.com/michaelellis003/uv-python-template/commit/e05cd19b61854a22960d77c2fa9907a5263e0c72))

### Features

- **cli**: Add --github flag for full GitHub repo setup
  ([#28](https://github.com/michaelellis003/uv-python-template/pull/28),
  [`e05cd19`](https://github.com/michaelellis003/uv-python-template/commit/e05cd19b61854a22960d77c2fa9907a5263e0c72))


## v1.8.0 (2026-02-18)

### Bug Fixes

- **e2e**: Exclude test_init.py from init script reference check
  ([`eb65a75`](https://github.com/michaelellis003/uv-python-template/commit/eb65a750709bf08b52a1694eae32322a30fc5b95))

- **init**: Add .gitattributes, fix sed delimiter, expand stale check
  ([`4de0690`](https://github.com/michaelellis003/uv-python-template/commit/4de0690da34a79a8907381d7a6bf5ff8aa23ced8))

- **init**: Add cli/ to cleanup and exclusions
  ([`03caaa5`](https://github.com/michaelellis003/uv-python-template/commit/03caaa5a4347a49d81800aba54062f1b61e6d827))

- **init**: Escape quotes and backslashes for TOML strings
  ([`4e50446`](https://github.com/michaelellis003/uv-python-template/commit/4e50446aa35ff194b3be5840db6dd633b883d4bc))

- **init**: Exclude generated dirs from stale reference check
  ([`d28e2b3`](https://github.com/michaelellis003/uv-python-template/commit/d28e2b3254fa8b51294e0282aab72539ad08a4ab))

- **init**: Require non-empty description and harden E2E checks
  ([`b0dab30`](https://github.com/michaelellis003/uv-python-template/commit/b0dab30266a69814200930bc7ee9fcaf0b0d547b))

- **init**: Strip cli-tests from ci.yml, reject trailing hyphens in names, use RELEASE_TOKEN
  ([`deb9361`](https://github.com/michaelellis003/uv-python-template/commit/deb93616873f19d9e17461e726c8efbaf4602892))

### Continuous Integration

- **cli**: Add cli-tests job and cli-release workflow
  ([`5a77583`](https://github.com/michaelellis003/uv-python-template/commit/5a77583aef5ebcdbe01649ee7742a8f3b869ac55))

### Documentation

- Add pypkgkit CLI documentation
  ([`35b4805`](https://github.com/michaelellis003/uv-python-template/commit/35b4805a32f5b09838c4e06529b13884b99f4cf9))

### Features

- **cli**: Add pypkgkit CLI package for scaffolding projects
  ([`0afc5a0`](https://github.com/michaelellis003/uv-python-template/commit/0afc5a0e30ec5d4801417d1b2885aeb5d7222b13))

- **e2e**: Update E2E tests to use init.py instead of init.sh
  ([`33f974e`](https://github.com/michaelellis003/uv-python-template/commit/33f974eb78efa89efc9b1d1a94d246d3cfc0f2ac))

- **init**: Add CLI, prompts, and orchestration to init.py
  ([`c73c749`](https://github.com/michaelellis003/uv-python-template/commit/c73c749a1a651aab97d74e908a4de70281daa845))

- **init**: Add file operation functions to init.py
  ([`79253fe`](https://github.com/michaelellis003/uv-python-template/commit/79253fe08ae6d43bcea4b56441a561c9295108e5))

- **init**: Add scripts/init.py with pure validation and transform logic
  ([`1ca17a8`](https://github.com/michaelellis003/uv-python-template/commit/1ca17a8231b7daa83c1d8765edad570008ca0643))

- **init**: Migrate integration tests to call init.py
  ([`7b0527d`](https://github.com/michaelellis003/uv-python-template/commit/7b0527d7a6e802f90b42c19bca4b88ce74e71be6))

- **init**: Remove init.sh and update all documentation
  ([`f7880a3`](https://github.com/michaelellis003/uv-python-template/commit/f7880a370d4d038dbf66651b91a0c68f514a2fe2))


## v1.7.3 (2026-02-16)

### Bug Fixes

- **init**: Prevent awk backslash interpretation in description
  ([`d1d58fd`](https://github.com/michaelellis003/uv-python-template/commit/d1d58fdcb645f7db7238e4af67e152525e6bce1a))


## v1.7.2 (2026-02-16)

### Bug Fixes

- **init**: Escape author sed, validate inputs, harden CI and release
  ([`bacc769`](https://github.com/michaelellis003/uv-python-template/commit/bacc769520ac893ae46a2179a6d490a7c6680140))

- **init**: Handle API rate limits and exclude binary files from sed
  ([`bdf9858`](https://github.com/michaelellis003/uv-python-template/commit/bdf985845d26ec4b2c7406a15504102fe7bacf00))

- **init**: Remove E2E section from README during cleanup
  ([`709409e`](https://github.com/michaelellis003/uv-python-template/commit/709409e65889ddb0cf37e1e1ddfd32e8ce34bf52))

- **init**: Validate inputs, surface sed errors, harden CI workflows
  ([`03b35b6`](https://github.com/michaelellis003/uv-python-template/commit/03b35b6e79ef264ecf0c2ad06eb0e9078bf01115))


## v1.7.1 (2026-02-16)

### Bug Fixes

- **init**: Validate flag args, escape sed metacharacters, expand checks
  ([`6d6f0ae`](https://github.com/michaelellis003/uv-python-template/commit/6d6f0aec293acf78e23446142a4b39a0a323f840))


## v1.7.0 (2026-02-16)

### Bug Fixes

- **init**: Improve error handling and fix docs bugs
  ([`e568ddc`](https://github.com/michaelellis003/uv-python-template/commit/e568ddc15f7e67a2d99cd18deacedffc5992074c))

### Features

- **e2e**: Add Docker-based end-to-end test suite
  ([`c5f1ae7`](https://github.com/michaelellis003/uv-python-template/commit/c5f1ae72f643e24a7ea5506ce461018799f11a9e))


## v1.6.0 (2026-02-16)

### Bug Fixes

- **ci**: Skip integration tests on macOS/Windows, fix build pip install
  ([`6c8dcc8`](https://github.com/michaelellis003/uv-python-template/commit/6c8dcc8f767ac729c69b7ac08efdbe738164185c))

- **init**: Update meta.yaml license, validation message, and python3 check
  ([`d33aa61`](https://github.com/michaelellis003/uv-python-template/commit/d33aa61656e78b4b4cfb9328ab854ebab65f2372))

- **pre-commit**: Exclude recipe/meta.yaml from check-yaml hook
  ([`47a9811`](https://github.com/michaelellis003/uv-python-template/commit/47a981179fefe6bc6a3d033b1ac9ef97f92ffbd2))

### Documentation

- **readme**: Add GitHub Pages setup instructions
  ([`627d4f3`](https://github.com/michaelellis003/uv-python-template/commit/627d4f38dfda729ca2da1fe7d1dcdc06c9fc3d7d))

### Features

- **init**: Add post-init validation, lock-check CI job, and UX improvements
  ([`4e6a244`](https://github.com/michaelellis003/uv-python-template/commit/4e6a24406ceb7e91c75ebbefd944659c0f071cf0))

- **init**: Add template tests, license bug fixes, and config updates
  ([`323ab87`](https://github.com/michaelellis003/uv-python-template/commit/323ab87a9d0db3a4c65dc0803c519cfb5dec828c))

- **publish**: Add PyPI, TestPyPI, and conda-forge publishing support
  ([`9d6861c`](https://github.com/michaelellis003/uv-python-template/commit/9d6861ca2f985673968b336391f36571b84283b3))


## v1.5.0 (2026-02-15)

### Features

- **docs**: Add MkDocs documentation with GitHub Pages deployment
  ([`cd3a89f`](https://github.com/michaelellis003/uv-python-template/commit/cd3a89fa6831f16adb3a64223d3151ae9a8baaa6))


## v1.4.2 (2026-02-15)

### Bug Fixes

- **ci**: Add gate job, timeouts, and harden config
  ([`2f2cbb6`](https://github.com/michaelellis003/uv-python-template/commit/2f2cbb6faf906ae509eeffce990b7ba70893a9ee))


## v1.4.1 (2026-02-15)

### Bug Fixes

- **template**: Correct URLs, docs, and hook matching
  ([`4c4d91f`](https://github.com/michaelellis003/uv-python-template/commit/4c4d91ffc81ae84d7f84a8fbd2b7d111518185e2))


## v1.4.0 (2026-02-15)

### Features

- **ci**: Add dedicated coverage CI job as required PR check
  ([`eed184d`](https://github.com/michaelellis003/uv-python-template/commit/eed184d48b9b104304a8e6313973a154d77d5c31))

- **template**: Improve template with review findings
  ([`29e3b10`](https://github.com/michaelellis003/uv-python-template/commit/29e3b101a3d36ab459f48f38242d69ab5c5eee92))


## v1.3.0 (2026-02-15)

### Bug Fixes

- **template**: Address review findings across template repo
  ([`a7cd545`](https://github.com/michaelellis003/uv-python-template/commit/a7cd54508bab4b929f0b1169364fbbf22e3a935c))

### Features

- **init**: Self-clean after initialization
  ([`b8f6346`](https://github.com/michaelellis003/uv-python-template/commit/b8f63462441c903bdcdea2a2f14c72a81aa86ad7))

### Refactoring

- **scripts**: Address review feedback for init.sh and setup-repo.sh
  ([`26740ed`](https://github.com/michaelellis003/uv-python-template/commit/26740ed785735b6ee67fb70278613a02572aee84))


## v1.2.0 (2026-02-15)

### Documentation

- **rules**: Add design principles rule file
  ([`67ab2c7`](https://github.com/michaelellis003/uv-python-template/commit/67ab2c78c66369a2e76c3566140e2a980322aef7))

- **rules**: Add error handling and Python idioms rule files
  ([`3463ea7`](https://github.com/michaelellis003/uv-python-template/commit/3463ea774763c2400842939e58021c24d2c08d26))

### Features

- **onboarding**: Add interactive init script for template setup
  ([`369c807`](https://github.com/michaelellis003/uv-python-template/commit/369c807d02e92ef333d1c3e3a813280cbef7831b))


## v1.1.2 (2026-02-15)

### Bug Fixes

- Address review findings across template
  ([`ba5c88b`](https://github.com/michaelellis003/uv-python-template/commit/ba5c88b327acf3bf5f4b0959fe2d897ee7636dd1))

### Chores

- Add setup-repo.sh for one-time branch protection config
  ([`09e58ba`](https://github.com/michaelellis003/uv-python-template/commit/09e58ba3f378607a3e89a4bccd06509be2f60a4d))

### Continuous Integration

- **deps**: Bump actions/checkout from 4 to 6
  ([`7c800f3`](https://github.com/michaelellis003/uv-python-template/commit/7c800f30771dc244138e5e024516e994135f31f0))

### Documentation

- Add branch protection setup note for Dependabot auto-merge
  ([`d3a3ece`](https://github.com/michaelellis003/uv-python-template/commit/d3a3ece862b3d661fd119f6db89dd420fafe1977))


## v1.1.1 (2026-02-15)

### Bug Fixes

- Address template review findings across CI, linting, and tests
  ([`04cfa29`](https://github.com/michaelellis003/uv-python-template/commit/04cfa29032a00a3065e38c18898bdb715dc52b39))

### Continuous Integration

- **dependabot**: Add auto-merge workflow for minor/patch updates
  ([`b8966e0`](https://github.com/michaelellis003/uv-python-template/commit/b8966e0f240de87a599dce7d5716a94328dc7eb9))


## v1.1.0 (2026-02-15)

### Chores

- **config**: Improve pyproject.toml metadata and tool settings
  ([`1e255af`](https://github.com/michaelellis003/uv-python-template/commit/1e255af3552b69c4d692d3fb45b86d2a8fd10dc4))

- **editor**: Add .editorconfig for non-Python files
  ([`ec0b4d3`](https://github.com/michaelellis003/uv-python-template/commit/ec0b4d35e05a30624e8c0110d13283f1f2093071))

- **pre-commit**: Add standard validation hooks
  ([`23114e7`](https://github.com/michaelellis003/uv-python-template/commit/23114e74d06c1c2068b0fe886513bacaa3ce7e35))

### Continuous Integration

- **python**: Add Python 3.13 to test matrix
  ([`b08c77e`](https://github.com/michaelellis003/uv-python-template/commit/b08c77eba9cadbcf7bdde48eb22060de4074248e))

- **python**: Replace .python-versions with hardcoded CI matrix
  ([`3eadee9`](https://github.com/michaelellis003/uv-python-template/commit/3eadee984a3265b30f127174f7ed780589b577bb))

### Documentation

- **github**: Add issue and PR templates
  ([`082ab3a`](https://github.com/michaelellis003/uv-python-template/commit/082ab3aea033c3923c74b09d67c1e1f8feec44bd))

- **readme**: Update structure and Python version references
  ([`5e77612`](https://github.com/michaelellis003/uv-python-template/commit/5e776120f4f9e459c072dca7dd590e341f65984d))

### Features

- **package**: Add py.typed marker and __version__ export
  ([`0e7859e`](https://github.com/michaelellis003/uv-python-template/commit/0e7859e8a7fc2c80a00ef4f216c2ae67bf6511f7))

### Testing

- **demo**: Rename tests to convention and add boundary cases
  ([`6ef7e4a`](https://github.com/michaelellis003/uv-python-template/commit/6ef7e4aa58106412601672cb44d284369141b3dd))


## v1.0.1 (2026-02-15)

### Bug Fixes

- **ci**: Add ruff as dev dependency for direct CI invocation
  ([`9897e0a`](https://github.com/michaelellis003/uv-python-template/commit/9897e0a33df54ba127cb9cefe8a6dd0f103efe33))


## v1.0.0 (2026-02-15)

### Bug Fixes

- **ci**: Run semantic-release via CLI instead of Docker action
  ([`c47687b`](https://github.com/michaelellis003/uv-python-template/commit/c47687b02ec68b3679e96617f1f97c39e6324e3d))

### Continuous Integration

- Overhaul CI/CD pipeline with parallel jobs and automated releases
  ([`22c35ee`](https://github.com/michaelellis003/uv-python-template/commit/22c35ee81abcb189fa703587f15f3965d72ab0d1))

### Documentation

- **ci**: Address review findings for CI/CD pipeline
  ([`84b6fd0`](https://github.com/michaelellis003/uv-python-template/commit/84b6fd08bcf66c879865fdd371691295be488b5b))


## v0.3.0 (2026-02-15)

### Bug Fixes

- **ci**: Filter empty string from python version matrix
  ([`ebc1919`](https://github.com/michaelellis003/uv-python-template/commit/ebc19197de18c875d0e735acebcd7988d21bcb86))

### Chores

- Bump version to 0.3.0
  ([`6c6330f`](https://github.com/michaelellis003/uv-python-template/commit/6c6330f0a8ff8e0d7168fc042e6c6c3ae6d70f6e))

- Update uv.lock for v0.3.0
  ([`3082d24`](https://github.com/michaelellis003/uv-python-template/commit/3082d2405bee1d56a45fe97d371e6128406d918d))

- **deps**: Migrate from poetry to uv
  ([`bac81f2`](https://github.com/michaelellis003/uv-python-template/commit/bac81f220c3742f898edce763c45563458208442))

### Documentation

- Add version bump step to development lifecycle
  ([`684f3b0`](https://github.com/michaelellis003/uv-python-template/commit/684f3b0987ca294b468731b8750a64eb8eb8db65))

- Rewrite docs as template guide and add docs lifecycle step
  ([`53b9b89`](https://github.com/michaelellis003/uv-python-template/commit/53b9b891992eb8b3767e28ba49c0ee3cf022b486))


## v0.2.0 (2026-02-15)

- Initial Release
