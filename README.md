# tvh-auto-power
Shutdown and wake up a Tvheadend server automatically

## Step 1:

Copy this script to some directory like `/usr/local/bin` and make it executeable.

## Step 2:

Change URL, username and password if necessary.

## Step 3:

Add a cronjob like this to get this script running:

```
*/5 * * * * sleep 15m && /usr/local/bin/tvh-auto-power.py
```

The sleep commands prevents the server to shutdown immeadeatly after boot.
