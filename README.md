# HMAC Addresses

Privacy-preserving address encoding using HMAC-SHA256 for secure matching without exposing raw address data.

## Overview

This project combines **BERT-based Chinese address parsing** with **HMAC-SHA256** token-level encoding for privacy-preserving address matching.

### BERT Address Parser

Uses the fine-tuned BERT model [`jiaqianjing/chinese-address-ner`](https://huggingface.co/jiaqianjing/chinese-address-ner) for token classification to parse Chinese addresses into structured components: province, city, district, street, road, community, unit, etc.

### HMAC Encoding

**HMAC-SHA256** is applied at the token level to encode address strings before matching. Two tokenization strategies are supported:

- **1-gram**: Character-level hashing — each character is hashed individually
- **Bigram**: Consecutive character pairs (with optional start/end tokens) hashed as units

### Similarity Metrics

The notebooks implement several similarity measures over HMAC-encoded sequences: Levenshtein, Jaro, Jaro-Winkler, Q-gram, and Jaccard.

## Requirements

- Python 3.11+

## Setup

```bash
uv sync
```

## Project Structure

- `main.py` — Entry point
- `HMAC_encoding_test.ipynb` — HMAC encoding, address parsing, and similarity experiments
- `HMAC_encoding_test-explained.ipynb` — Annotated version with detailed explanations

## License

MIT
