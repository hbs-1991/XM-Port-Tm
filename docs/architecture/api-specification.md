# API Specification

## REST API Specification

```yaml
openapi: 3.0.3
info:
  title: XM-Port API
  version: 1.0.0
  description: AI-Powered Customs Declaration Assistant API for automated HS code matching and ASYCUDA XML generation
  contact:
    name: XM-Port Support
    email: support@xm-port.com
  license:
    name: Proprietary
servers:
  - url: https://api.xm-port.com/v1
    description: Production server
  - url: https://api-staging.xm-port.com/v1
    description: Staging server
  - url: http://localhost:8000/api/v1
    description: Development server
