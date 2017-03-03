# Change Log

## [v0.8.2](https://github.com/ably/ably-python/tree/v0.8.2)

[Full Changelog](https://github.com/ably/ably-python/compare/v0.8.1...v0.8.2)

**Implemented enhancements:**

- PaginatedResult attributes [\#70](https://github.com/ably/ably-python/issues/70)
- 0.8.x finalisation [\#48](https://github.com/ably/ably-python/issues/48)

**Fixed bugs:**

- Do not persist authorise attributes force & timestamp  [\#52](https://github.com/ably/ably-python/issues/52)

**Closed issues:**

- Publish on PyPI [\#50](https://github.com/ably/ably-python/issues/50)

**Merged pull requests:**

- RSC7, RSC11, RSC15, RSC19 [\#81](https://github.com/ably/ably-python/pull/81) ([jdavid](https://github.com/jdavid))
- updated reqests version in requirements [\#67](https://github.com/ably/ably-python/pull/67) ([essweine](https://github.com/essweine))

## [v0.8.1](https://github.com/ably/ably-python/tree/v0.8.1) (2016-03-22)
[Full Changelog](https://github.com/ably/ably-python/compare/v0.8.0...v0.8.1)

**Implemented enhancements:**

- Don't require get\_default\_params for encryption [\#56](https://github.com/ably/ably-python/issues/56)
- Consistent README [\#8](https://github.com/ably/ably-python/issues/8)

**Closed issues:**

- when msgpack enabled, python 2 string literals are encoded as binaries [\#60](https://github.com/ably/ably-python/issues/60)

**Merged pull requests:**

- Python 2: assume str is intended as a string [\#64](https://github.com/ably/ably-python/pull/64) ([SimonWoolf](https://github.com/SimonWoolf))
- Implement latest encryption spec [\#63](https://github.com/ably/ably-python/pull/63) ([SimonWoolf](https://github.com/SimonWoolf))
- RSA7b4, RSA8f3, RSA8f4 [\#62](https://github.com/ably/ably-python/pull/62) ([fjsj](https://github.com/fjsj))
- RSA7a4 [\#61](https://github.com/ably/ably-python/pull/61) ([fjsj](https://github.com/fjsj))
- RSA7a2 [\#59](https://github.com/ably/ably-python/pull/59) ([fjsj](https://github.com/fjsj))
- RSA12 [\#58](https://github.com/ably/ably-python/pull/58) ([fjsj](https://github.com/fjsj))

## [v0.8.0](https://github.com/ably/ably-python/tree/v0.8.0) (2016-03-10)
**Implemented enhancements:**

- Switch arity of auth methods [\#42](https://github.com/ably/ably-python/issues/42)
- API changes Apr 2015 [\#7](https://github.com/ably/ably-python/issues/7)
- Change of repository name imminent [\#4](https://github.com/ably/ably-python/issues/4)

**Fixed bugs:**

- Switch arity of auth methods [\#42](https://github.com/ably/ably-python/issues/42)
- Use sandbox not staging [\#38](https://github.com/ably/ably-python/issues/38)
- API changes Apr 2015 [\#7](https://github.com/ably/ably-python/issues/7)

**Closed issues:**

- AblyException does not have \_\_str\_\_ [\#32](https://github.com/ably/ably-python/issues/32)
- Add a requirements-test.txt [\#29](https://github.com/ably/ably-python/issues/29)
- Fix message on test [\#23](https://github.com/ably/ably-python/issues/23)
- Rename test\_channels\_remove to test\_channels\_release [\#20](https://github.com/ably/ably-python/issues/20)
- Add comments in Python 2/3 code at ably/rest/channel.py [\#19](https://github.com/ably/ably-python/issues/19)
- Support for 2.6 [\#10](https://github.com/ably/ably-python/issues/10)
- Spec validation [\#9](https://github.com/ably/ably-python/issues/9)

**Merged pull requests:**

- Fixes for PyPI publishing \(already published\) [\#57](https://github.com/ably/ably-python/pull/57) ([fjsj](https://github.com/fjsj))
- RSL1g [\#55](https://github.com/ably/ably-python/pull/55) ([fjsj](https://github.com/fjsj))
- Ensure that force and timestamp are not stored in authorise [\#53](https://github.com/ably/ably-python/pull/53) ([meiralins](https://github.com/meiralins))
- Improve readme, fix setup.py and add support for Python 3.5. [\#51](https://github.com/ably/ably-python/pull/51) ([meiralins](https://github.com/meiralins))
- Minor adjustments to fit specs. [\#49](https://github.com/ably/ably-python/pull/49) ([meiralins](https://github.com/meiralins))
- More changes to auth to fit specs. [\#47](https://github.com/ably/ably-python/pull/47) ([meiralins](https://github.com/meiralins))
- Changes to auth to fit specs. [\#46](https://github.com/ably/ably-python/pull/46) ([aericson](https://github.com/aericson))
- Changes to client options [\#44](https://github.com/ably/ably-python/pull/44) ([aericson](https://github.com/aericson))
- RSA10: Auth\#authorise [\#43](https://github.com/ably/ably-python/pull/43) ([aericson](https://github.com/aericson))
- Done with stats, as well as varying every test to each protocol \(G1\) [\#41](https://github.com/ably/ably-python/pull/41) ([aericson](https://github.com/aericson))
- Requirements test [\#40](https://github.com/ably/ably-python/pull/40) ([aericson](https://github.com/aericson))
- Now when sending binary data messages one should use bytearray [\#39](https://github.com/ably/ably-python/pull/39) ([aericson](https://github.com/aericson))
- Fix travis [\#37](https://github.com/ably/ably-python/pull/37) ([aericson](https://github.com/aericson))
- Rsc7 and rsc18 [\#36](https://github.com/ably/ably-python/pull/36) ([aericson](https://github.com/aericson))
- Message pack [\#35](https://github.com/ably/ably-python/pull/35) ([aericson](https://github.com/aericson))
- Add Query time parameter TO3j10 and RSA9d [\#34](https://github.com/ably/ably-python/pull/34) ([aericson](https://github.com/aericson))
- Missing channel tests [\#33](https://github.com/ably/ably-python/pull/33) ([aericson](https://github.com/aericson))
- RSL2a and RSL2b3 - Channel\#history [\#31](https://github.com/ably/ably-python/pull/31) ([aericson](https://github.com/aericson))
- Message encoding [\#30](https://github.com/ably/ably-python/pull/30) ([aericson](https://github.com/aericson))
- RSC13 and RSC15 - Hosts fallback and timeouts [\#28](https://github.com/ably/ably-python/pull/28) ([fjsj](https://github.com/fjsj))
- RSP Presence, TG PaginatedResult and Presence Message TP [\#26](https://github.com/ably/ably-python/pull/26) ([aericson](https://github.com/aericson))
- \(RSL1d\) Indicates an error if the message was not successfully published to Ably [\#25](https://github.com/ably/ably-python/pull/25) ([fjsj](https://github.com/fjsj))
- Fix wrongly named tests [\#24](https://github.com/ably/ably-python/pull/24) ([fjsj](https://github.com/fjsj))
- RSL1a, RSL1b, RSL1e and RSL1c \(incomplete\) [\#21](https://github.com/ably/ably-python/pull/21) ([fjsj](https://github.com/fjsj))
- Channels - RSN1 to RSN4a [\#18](https://github.com/ably/ably-python/pull/18) ([fjsj](https://github.com/fjsj))
- Rsc1 api constructor [\#16](https://github.com/ably/ably-python/pull/16) ([aericson](https://github.com/aericson))
- Fix travis [\#15](https://github.com/ably/ably-python/pull/15) ([fjsj](https://github.com/fjsj))
- Fix tests except for crypto, messagepack and stats [\#14](https://github.com/ably/ably-python/pull/14) ([aericson](https://github.com/aericson))
- Fix the readme with the examples and the links [\#5](https://github.com/ably/ably-python/pull/5) ([matrixise](https://github.com/matrixise))
- Ably Python Rest Library Testing Fixes [\#3](https://github.com/ably/ably-python/pull/3) ([jcrubino](https://github.com/jcrubino))



\* *This Change Log was automatically generated by [github_changelog_generator](https://github.com/skywinder/Github-Changelog-Generator)*
