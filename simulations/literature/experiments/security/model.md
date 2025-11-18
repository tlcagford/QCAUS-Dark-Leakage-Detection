# security/model.md

Security model & proof sketch — Quantum-Secure Dark Net

## Adversary model (Eve)
- Eve can intercept classical photon channels and has advanced quantum computing resources.
- Eve may have detectors sensitive to dark-sector excitations up to coupling threshold g_Eve.

## Physical assumptions to validate experimentally
- A1: Converter (photon ↔ dark) exists with coupling g and efficiency η_conv and preserves coherence with fidelity F_conv.
- A2: Dark-sector propagation coupling to SM is bounded and included in the security analysis.
- A3: Reconversion efficiency η_rec and fidelity F_rec are measured.
- A4: Classical channels for authentication are secure.

## Security proof outline
1. Model channel E_{g,η} and bound Eve's accessible mutual information I(E;K).
2. Perform parameter estimation during runs to bound channel parameters.
3. Use entropic bounds / Devetak–Winter to compute secure key rate.
4. Provide composable security statement based on experimental bounds.

## Required deliverables
- Measured bounds on g, η_conv, η_rec, noise spectral density and repeatable parameter estimation procedure.
