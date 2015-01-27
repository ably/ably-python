### Coder Log
> **Sunday January 25 2015**
    Completed thorough examination of test suite and parts of the main library.  The key_str created during test setup is suspect as the new triplet format of `<appid><keyid><keysecret>` was present but the rest of the Test suite namely ably/types/options was enforcing the `<keyid><keysecret>` configuration.  Likely the rest of the lib does to and will have to be adjusted to post the proper format on requests.  70 tests are failing but **the good news is** the initial the test setup test/ably/restsetup.py is pass params as expected by the main library and the main feature tests at least now run where prior they would fail to initialize at all.
[last commit](https://github.com/jcrubino/ably-python-rest/commit/ba464f7)



> **Sunday January 26 2015**
    Reinvestigated key_str formation.  The prior code was misidentifiying the appspec App ID by just requesting "id" in its place.  Changed to "appId". Added and turned on more logging debug print outs to verify requests and responses.  Test suite appears to be authenticating but individual tests are not passing at this time.
[last commit](https://github.com/jcrubino/ably-python-rest/commit/9214d1a)
