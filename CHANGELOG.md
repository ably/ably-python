# Change Log

## [v1.0.2](https://github.com/ably/ably-python/tree/v1.0.2)

[Full Changelog](https://github.com/ably/ably-python/compare/v1.0.1...v1.0.2)

**Fixed bugs:**

- HTTP connection pooling [\#133](https://github.com/ably/ably-python/issues/133)
- Timeouts when publishing messages [\#111](https://github.com/ably/ably-python/issues/111)
- AWS lambda packaging [\#97](https://github.com/ably/ably-python/issues/97)
- Rate limit requests to sandbox app [\#68](https://github.com/ably/ably-python/issues/68)

**Closed issues:**

- TokenRequest ttl unit discrepancy [\#104](https://github.com/ably/ably-python/issues/104)
- Python subscribe? [\#100](https://github.com/ably/ably-python/issues/100)

**Merged pull requests:**

- Fix README so it doesn't mislead ttl to be in s [\#105](https://github.com/ably/ably-python/pull/105) ([jdavid](https://github.com/jdavid))
- Fix tests [\#103](https://github.com/ably/ably-python/pull/103) ([jdavid](https://github.com/jdavid))
- Update README with supported platforms [\#102](https://github.com/ably/ably-python/pull/102) ([funkyboy](https://github.com/funkyboy))

## [v1.0.1](https://github.com/ably/ably-python/tree/v1.0.1) (2017-12-20)
[Full Changelog](https://github.com/ably/ably-python/compare/v1.0.0...v1.0.1)

**Implemented enhancements:**

- Fix HttpRequest & HttpRetry timeouts [\#86](https://github.com/ably/ably-python/issues/86)
- Cast TTL to integer [\#71](https://github.com/ably/ably-python/issues/71)
- Make PyCrypto optional [\#65](https://github.com/ably/ably-python/issues/65)

**Fixed bugs:**

- Travis random failures [\#88](https://github.com/ably/ably-python/issues/88)

**Closed issues:**

- pycrypto --\> pycryptodome [\#96](https://github.com/ably/ably-python/issues/96)
- `ably` module seems to be broken / empty in some circumstances [\#95](https://github.com/ably/ably-python/issues/95)
- installing via pip installs a more restrictive version of requests [\#91](https://github.com/ably/ably-python/issues/91)
- Add test coverage to prevent possible MsgPack regression [\#89](https://github.com/ably/ably-python/issues/89)
- 1.0 spec review [\#84](https://github.com/ably/ably-python/issues/84)
- When using python2 with msgpack, dicts are not encoded correctly [\#72](https://github.com/ably/ably-python/issues/72)

**Merged pull requests:**

- Fix unit tests [\#99](https://github.com/ably/ably-python/pull/99) ([jdavid](https://github.com/jdavid))
- Switch to cryptodome [\#98](https://github.com/ably/ably-python/pull/98) ([jdavid](https://github.com/jdavid))
- ttl: use isinstance instead of type [\#94](https://github.com/ably/ably-python/pull/94) ([jdavid](https://github.com/jdavid))
- Fix Flake8 warnings regarding spacing [\#93](https://github.com/ably/ably-python/pull/93) ([sginn](https://github.com/sginn))
- Bumped upper limit on requests library, and removed websocket [\#92](https://github.com/ably/ably-python/pull/92) ([sginn](https://github.com/sginn))
- Fix \#65, \#71, \#72, \#86 and \#89 [\#90](https://github.com/ably/ably-python/pull/90) ([jdavid](https://github.com/jdavid))

## [v1.0.0](https://github.com/ably/ably-python/tree/v1.0.0) (2017-03-07)
[Full Changelog](https://github.com/ably/ably-python/compare/v0.8.2...v1.0.0)

### v1.0 release and upgrade notes from v0.8

- See https://github.com/ably/docs/issues/235

**Implemented enhancements:**

- RSC19\*, HP\* - New REST \#request method + HttpPaginatedResponse type [\#78](https://github.com/ably/ably-python/issues/78)
- Update REST library for realtime platform to v1.0 specification [\#77](https://github.com/ably/ably-python/issues/77)

**Closed issues:**

- requests version pin too strict? [\#66](https://github.com/ably/ably-python/issues/66)

**Merged pull requests:**

- Issue\#84 TP4, RSC15a \(test\), RSC19e \(test\), .. [\#87](https://github.com/ably/ably-python/pull/87) ([jdavid](https://github.com/jdavid))
- Fix issue 72 [\#85](https://github.com/ably/ably-python/pull/85) ([jdavid](https://github.com/jdavid))
- Fix README, now using pytest instead of nose [\#83](https://github.com/ably/ably-python/pull/83) ([jdavid](https://github.com/jdavid))
- RSA5, RSA6, RSA10, RSL\*, TM\*, TE6, TD7 [\#82](https://github.com/ably/ably-python/pull/82) ([jdavid](https://github.com/jdavid))

## [v0.8.2](https://github.com/ably/ably-python/tree/v0.8.2) (2017-02-17)
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
- Several python code repo improvements [\#73](https://github.com/ably/ably-python/pull/73) ([txomon](https://github.com/txomon))
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
