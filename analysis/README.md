Internal package code goes in the `internal` folder.

Importing from the internal package is done like this:

```python
from analysis.internal.<something> import <something>
```

Port 8001 is used for the analysis api.

See the `docker-compose.yml` file for the path mounted as `/mnt/oxn-data/experiments`.
You can change it to your liking.

Then for local development in docker, run:

```bash
docker compose up
```
From the analysis folder.