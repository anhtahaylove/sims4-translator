# Konflux CI Review

Reviewed: 2026-05-27

Konflux CI is a Kubernetes-native software factory focused on signed builds,
SLSA provenance, SBOMs, policy checks, and release orchestration. It is useful
as a supply-chain reference, but it is intentionally much larger than this
desktop app's release needs.

## Useful ideas adopted

- Treat release evidence as a first-class artifact, not an afterthought.
- Verify the published release itself, not only the build artifact.
- Keep artifact signing, provenance, and release attestation in the automated
  release path so maintainers do not need manual post-release steps.

## Ideas not adopted

- Tekton/Kubernetes orchestration is too heavy for a small PySide6 desktop app
  that already builds cleanly on GitHub Actions.
- Conforma policy gates and OCI image promotion do not match the current ZIP
  release format.
- Full SBOM infrastructure is a possible future improvement, but it should be
  added only if it can stay lightweight and avoid new runtime dependencies.

## Repo decision

The practical upgrade is to use GitHub immutable releases and verify the
generated release attestation with `gh release verify` and
`gh release verify-asset`. The existing GitHub Artifact Attestations and cosign
keyless bundle remain useful because they prove build workflow provenance for
the ZIP asset.
