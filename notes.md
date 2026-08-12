issue link: [text](https://github.com/Michele0303/tiktok-live-recorder/issues/434)

Issue says Press q to stop recoding but i did not find this logic in there

Going to a create a test case to recretate the inf loop 

recording doest stop when live ends.

changed tiktok recorder and follower mode loop logic to use stop event, built a unit test to check that thread is being handleded gracefully. replacing the booling stop logic.  