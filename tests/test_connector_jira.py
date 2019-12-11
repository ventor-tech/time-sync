from synchronizer.connectors.jira import JiraConnector


def test_round_seconds():
    """
    Test if round_seconds_to_minutes working correctly
    """
    # Zero seconds shouldn't be changed
    assert JiraConnector.round_seconds(0) == 0

    # Always round to ceil number of minutes
    assert JiraConnector.round_seconds(1) == 60
    assert JiraConnector.round_seconds(30) == 60
    assert JiraConnector.round_seconds(59) == 60
    assert JiraConnector.round_seconds(60) == 60
    assert JiraConnector.round_seconds(300) == 300
    assert JiraConnector.round_seconds(1021) == 1080
