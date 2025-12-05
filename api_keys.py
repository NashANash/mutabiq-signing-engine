API_KEYS = {
  "test-key-123": "demo-client",
  "prod-key-abc": "first-customer"
}

def is_valid_key(key):
  return key in API_KEYS