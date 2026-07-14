# GCP livestream host

The production market stream runs on a dedicated private Compute Engine VM in
Frankfurt. The VM has no public IP or application ingress and reaches Artifact
Registry, Secret Manager, the HB Capital site, and YouTube through Cloud NAT.

`provision_stream.sh` creates the network, service account, repository, empty
Secret Manager secret, and a stopped `c3-standard-4` VM. It deliberately does
not upload a stream key or start a public broadcast.

`deploy_image.sh` builds the runtime with Cloud Build and publishes it to the
Frankfurt Artifact Registry repository. It refuses to run if `.env` would be
included in the upload.

The startup script installs `hb-livestream.service`. Set
`LIVESTREAM_AUTOSTART=true` only after a private smoke test and an explicit
decision to send live bits to YouTube.
