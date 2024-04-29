# Very Stupid Network Monitor

Scripts for monitoring the quality of a network and attempting to discern local network issues from ISP issues.

This is some garbage code I threw together in a couple of hours to solve a problem for which all the available solutions seemed to be absurd levels of overkill. It's not well written. It's not well documented. It's not fault tolerant. It has zero tests. No security measures have been taken. Normally I would be disgusted by this quality of code, right now I'm mostly disgusted by the quality of consumer ISPs in 2024.


## Client

The client is intended to run on any availale computer on the network, eg a Raspberry Pi. It advertises itself over MDNS and searches for other instances on the local network.

- A set of hard coded servers are pinged at a rough interval.
- Any other discovered instances are pinged at the same interval.
- Occassionally the results of those ping tests are uploaded to the server.
- Infrequently the server and other discovered instances transfer ~2MBib of random data each way. This is base64 encoded so it's ~2.6MB uncompressed.
- The results of the speed tests are uploaded to the server as well.
- Uploads of ping results that fail will be cached forever (hope you have enough RAM). Speed test results will be lost if they cannot be uploaded but the speed test will be repeated.


## Server

- Saves data provided to MongoDB (which is assumed to be local).
- Provides speed test endpoints.
