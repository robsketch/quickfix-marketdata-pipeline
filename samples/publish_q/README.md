# External Q Publisher Example

## Introduction

This directory contains an example of an external (non-TLS) Q publisher. It uses the `rt.qpk` and is similar to Q publisher described in the [RT Quickstart](https://code.kx.com/insights/microservices/rt/quickstart/docker-compose.html#publishing).

## Running the example

Download and extract the `rt.pk`:

```
curl -LO https://portal.dl.kx.com/assets/raw/rt/1.9.0/rt.1.9.0.qpk
unzip rt.1.9.0.qpk
```

Run the example:

```
q sample.q
```
