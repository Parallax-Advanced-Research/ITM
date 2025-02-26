# Generating Pydantic Models from OpenAPI Schema

Provides Python models generated from an OpenAPI schema using OpenAPI Generator. Use **Pydantic v1** for data validation
and parsing. The API client is also generated, only the models a included here.

## Prerequisites
```sh
npm install -g @openapitools/openapi-generator-cli

openapi-generator-cli generate \
  -i updated_insurance_schema.yaml \
  -g python-pydantic-v1 \
  -o generated-python-client \
  --package-name insurance