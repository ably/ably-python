from test.ably.restsetup import RestSetup

def setup_package():
    RestSetup.get_test_vars()

def teardown_package():
    RestSetup.clear_test_vars()

