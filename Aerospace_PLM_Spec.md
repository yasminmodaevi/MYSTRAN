# Aerospace PLM System Technical Specification (AeroPLM)

## 1. System Architecture Design

### 1.1 Overview
AeroPLM is designed as a high-performance, on-premise Product Lifecycle Management system tailored for the aerospace industry. It follows a 3-tier architecture to ensure modularity, security, and scalability.

### 1.2 Architecture Layers

#### 1.2.1 Presentation Layer (Frontend)
- **Technology:** React.js / TypeScript.
- **State Management:** Redux Toolkit or TanStack Query.
- **3D Visualization:** Three.js / WebGL for lightweight model viewing (STEP, JT, GLB).
- **Communication:** RESTful APIs with JSON payloads.

#### 1.2.2 Application Layer (Backend)
- **Framework:** FastAPI (Python 3.11+). Chosen for high performance, asynchronous support, and native OpenAPI documentation.
- **Workflow Engine:** SpiffWorkflow (Python-native BPMN 2.0 engine) to manage Change Management and Requirements Traceability.
- **Authentication:** OAuth2 with JWT. Support for MFA (TOTP/WebAuthn) and HSM-backed digital signatures for AS9100 compliance.
- **Task Queue:** Celery with Redis for long-running FEA data extraction and CAD translation tasks.

#### 1.2.3 Data & Storage Layer
- **Relational Database:** PostgreSQL. Stores metadata, item structures, BOM relationships, audit trails, and user permissions.
- **File Vault (NAS):** Standard Network Attached Storage (NAS) mapped as a secure mount point.
    - Files are stored using a content-addressable storage (CAS) pattern or a structured folder hierarchy to prevent filename collisions.
    - Versioned objects for raw mesh (`.dat`), results (`.op2`, `.res`), and CAD files.

### 1.3 Deployment Model
- **Environment:** On-premise Linux Server (Ubuntu 22.04 LTS or RHEL 9).
- **Containerization:** Docker & Docker Compose for easy deployment and isolation of services (App, DB, Redis, Worker).
- **Reverse Proxy:** Nginx with TLS 1.3 for secure communication and load balancing.

### 1.4 Security & Compliance (AS9100)
- **Encryption:** AES-256 for data at rest (via DB/Disk encryption) and TLS 1.3 for data in transit.
- **Audit Logging:** Every write operation is recorded in an immutable audit table including timestamp, user ID, IP address, and old/new values.
- **Electronic Signatures:** Support for 21 CFR Part 11 style signatures (Password re-entry + Reason code) backed by X.509 certificates.

## 2. Database Schema Specification

The schema is designed for PostgreSQL to handle complex relational data with referential integrity.

### 2.1 Core Item Schema
```sql
-- Base table for all managed objects
CREATE TABLE items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id VARCHAR(50) UNIQUE NOT NULL, -- Human readable ID (e.g., PART-0001)
    item_type VARCHAR(20) NOT NULL, -- 'PART', 'DOCUMENT', 'REQUIREMENT'
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    owner_id UUID REFERENCES users(id)
);

-- Version control for items
CREATE TABLE item_revisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_id UUID REFERENCES items(id),
    revision_label VARCHAR(10) NOT NULL, -- 'A', 'B', '01', etc.
    lifecycle_state VARCHAR(20) DEFAULT 'IN_WORK', -- 'IN_WORK', 'RELEASED', 'OBSOLETE'
    effective_date TIMESTAMP WITH TIME ZONE,
    release_date TIMESTAMP WITH TIME ZONE,
    change_notice_id UUID, -- Link to ECN
    metadata JSONB -- Flexible attributes for different item types
);
```

### 2.2 Multi-BOM Schema
```sql
-- Hierarchical relationships
CREATE TABLE bom_structures (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    parent_rev_id UUID REFERENCES item_revisions(id),
    child_item_id UUID REFERENCES items(id), -- Points to item, specific rev resolved by BOM rules
    quantity DECIMAL NOT NULL DEFAULT 1.0,
    bom_type VARCHAR(10) NOT NULL, -- 'EBOM', 'MBOM', 'SBOM'
    unit_of_measure VARCHAR(10) DEFAULT 'EA',
    find_number INTEGER, -- Position in the assembly
    UNIQUE (parent_rev_id, child_item_id, bom_type)
);
```

### 2.3 Change Management & Workflow
```sql
CREATE TABLE change_requests (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    cr_id VARCHAR(50) UNIQUE NOT NULL,
    title TEXT NOT NULL,
    severity VARCHAR(10),
    status VARCHAR(20),
    workflow_instance_id UUID -- Link to SpiffWorkflow execution
);

CREATE TABLE workflows (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(100),
    bpmn_xml TEXT, -- BPMN 2.0 XML definition
    version INTEGER
);
```

### 2.4 File & FEA Vaulting
```sql
CREATE TABLE file_vault (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    item_revision_id UUID REFERENCES item_revisions(id),
    file_name TEXT NOT NULL,
    file_path TEXT NOT NULL, -- Relative path in NAS
    file_type VARCHAR(20), -- 'CAD_MODEL', 'FEA_MESH', 'FEA_RESULT', 'PDF'
    file_hash TEXT NOT NULL, -- For integrity verification (AS9100)
    file_size BIGINT,
    is_latest BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

## 3. API & Service Design

AeroPLM uses FastAPI for a high-performance RESTful API.

### 3.1 Item Management API
- `GET /api/v1/items`: List items with filters (type, owner).
- `POST /api/v1/items`: Create new item.
- `GET /api/v1/items/{id}/revisions`: Get revision history.
- `POST /api/v1/items/{id}/revisions`: Create a new revision (Bump A -> B).

### 3.2 BOM Management API
- `GET /api/v1/bom/{rev_id}?type=EBOM`: Retrieve assembly structure.
- `POST /api/v1/bom/{rev_id}/add`: Add child item to BOM.
- `PATCH /api/v1/bom/{id}`: Update quantity or find number.

### 3.3 File & Vaulting Service
The vaulting service handles large file transfers to the NAS.
- `POST /api/v1/vault/upload`: Multi-part upload for large CAD/CAE files.
- `GET /api/v1/vault/download/{file_id}`: Stream file from NAS with range support.

### 3.4 FEA Workflow Service
Specialized service to handle MYSTRAN/Nastran data.
- `POST /api/v1/fea/process-results`: Trigger an asynchronous task to parse `.f06` or `.op2` files and extract critical results (Max Stress, Displacement) to store in the `item_revisions.metadata` JSONB field.
- `GET /api/v1/fea/compare/{rev_id1}/{rev_id2}`: Compare FEA results between two design iterations.

### 3.5 Workflow Engine Integration
- `POST /api/v1/workflow/start/{workflow_id}`: Initiate a BPMN process for ECR/ECN.
- `GET /api/v1/workflow/tasks`: List pending tasks for the current user.
- `POST /api/v1/workflow/tasks/{task_id}/complete`: Approve or reject a workflow step.

## 4. Integration & Compliance Blueprint

### 4.1 CAD/CAE Integration (CATIA, NX, Nastran)
To support both "embedded" and "loose" integrations:

1.  **AeroPLM Client Toolkit (ACT):** A Python-based CLI/Library that can be imported into CAD/CAE scripting environments (e.g., CATIA VBA, NX Open Python, Nastran input generation).
2.  **Metadata Extraction:**
    - For CATIA/NX: Extract Assembly Tree, Mass Properties, and Material data.
    - For Nastran/Ansys: Extract Load Cases, Boundary Conditions, and Result Summaries.
3.  **Sidecar Files:** Automatically generate lightweight visualization files (STEP/JT for CAD, GLB/JSON for FEA) during the check-in process to enable the web-based 3D viewer.

### 4.2 AS9100 Compliance Features
1.  **Configuration Control:** Strict enforcement of revision numbering and "Released" locking. Items in a released state cannot be modified without a new ECN.
2.  **Traceability Matrix:** Auto-generated view showing Requirements linked to Parts, and Parts linked to Test Results/FEA reports.
3.  **Audit Trail Implementation:**
    - Trigger-based logging in PostgreSQL.
    - Exportable Audit Reports (PDF/Excel) for external auditors.
4.  **Digital Signatures:** Integrated with the workflow engine. Signatories must re-authenticate and provide a "Statement of Intent" (e.g., "I approve this design for production").

## 5. Frontend & Visualization Strategy

### 5.1 Technology Stack
- **Framework:** React 18+ with TypeScript.
- **Component Library:** Tailwind CSS + Headless UI or Mantine for a clean, professional "Engineering" look.
- **Data Fetching:** TanStack Query (React Query) for efficient caching of large BOM trees.

### 5.2 3D Viewer Integration
- **Engine:** Three.js.
- **Format:** Primarily uses GLB (Binary glTF) for CAD visualization and custom BufferGeometry for FEA results (Mesh + Heatmap).
- **Features:**
    - Cross-sectioning.
    - Component selection/highlighting linked to the BOM tree.
    - Stress heatmap overlays for CAE result visualization.

### 5.3 Multi-BOM Visualization
- **BOM Grid:** A recursive grid component that allows users to toggle between EBOM, MBOM, and SBOM views.
- **Differencing Tool:** Visual "Diff" view to compare revisions or compare EBOM vs. MBOM, highlighting missing or extra components.
