# Part 3 Tool Contracts Under Stress

All three domain tools return the shared envelope `{ok, data, error}`. On success,
`ok` is `true` and `error` is `null`. On rejection, `ok` is `false`, `data` is
`null`, and `error` contains a short explanation.

## `search_trials`

Expected input schema:

```json
{"query": "string", "limit": "integer from 1 through 25"}
```

Rejected Part 2B input:

```json
{"query": "Seeded Clinical Trial 1", "limit": 26}
```

Returned error:

```json
{"ok": false, "data": null, "error": "limit must be an integer between 1 and 25"}
```

The call was rejected because 26 exceeds the bounded search-result limit of 25.

## `get_trial_details`

Expected input schema:

```json
{"nct_code": "string matching NCT########"}
```

Rejected Part 2B input:

```json
{"nct_code": "BAD8561"}
```

Returned error:

```json
{"ok": false, "data": null, "error": "nct_code must match NCT########"}
```

The call was rejected because the value does not use the required `NCT` prefix
followed by exactly eight digits.

## `summarize_sponsors`

Expected input schema:

```json
{"min_trials": "integer from 1 through 5000", "limit": "integer from 1 through 50"}
```

Rejected Part 2B input:

```json
{"min_trials": 5001, "limit": 3}
```

Returned error:

```json
{"ok": false, "data": null, "error": "min_trials must be an integer between 1 and 5000"}
```

The call was rejected because the requested minimum exceeds the 5,000 trials in
the seeded domain database.
