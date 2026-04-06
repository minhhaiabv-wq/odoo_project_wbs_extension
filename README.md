# Project WBS Extension

An Odoo addon for project WBS management, including:

- `project.task.phase` management
- WBS list, form, and calendar views
- Default grouping by `project_id` and `phase_id`
- `phase_id` integration in Timesheets

## Requirements

- Docker
- Docker Compose
- Git

## 1. Create the project folder

Example:

```powershell
mkdir odoo-wbs
cd odoo-wbs
mkdir custom_addons
mkdir config
```

## 2. Create the `docker-compose.yml` file

Create a `docker-compose.yml` file in the project root with the following content:

```yaml
services:
  db:
    image: postgres:17
    environment:
      - POSTGRES_DB=postgres
      - POSTGRES_USER=odoo
      - POSTGRES_PASSWORD=odoo
    volumes:
      - odoo-db-data:/var/lib/postgresql/data
    restart: always

  odoo:
    image: odoo:19
    depends_on:
      - db
    ports:
      - "8069:8069"
    environment:
      - HOST=db
      - USER=odoo
      - PASSWORD=odoo
    volumes:
      - odoo-web-data:/var/lib/odoo
      - ./custom_addons:/mnt/extra-addons
      - ./config/odoo.conf:/usr/lib/python3/dist-packages/odoo/odoo.conf
    restart: always

volumes:
  odoo-db-data:
  odoo-web-data:
```

All mounted paths above are relative to the project root.

## 3. Create the `custom_addons/project_wbs_extension` folder

```powershell
mkdir custom_addons\project_wbs_extension
```

## 4. Clone the addon repository into that folder

If you are already in the project root:

```powershell
git clone https://github.com/minhhaiabv-wq/odoo_project_wbs_extension.git custom_addons\project_wbs_extension
```

## 5. Create the `config/odoo.conf` file

Create `config/odoo.conf` with the following content:

```ini
[options]
addons_path = /usr/lib/python3/dist-packages/odoo/addons,/mnt/extra-addons

#database
db_host = db
#db_port = 5432
db_user = odoo
db_password = odoo
```

## 6. Start Docker

```powershell
docker compose up -d
```

Check container status:

```powershell
docker compose ps
```

## 7. Open Odoo

Open:

```text
http://localhost:8069
```

Create a database if this is the first run.

## 8. Install the `project_wbs_extension` addon

In Odoo:

1. Go to `Apps`
2. Click `Update Apps List`
3. Search for `Project WBS Extension`
4. Click `Install`

## 9. Upgrade the module after code changes

When the source code is updated:

```powershell
docker compose restart odoo
```

Then in Odoo:

1. Go to `Apps`
2. Search for `Project WBS Extension`
3. Click `Upgrade`

## 10. Main features

- `WBS` menu inside Project
- WBS management based on `project.task.phase`
- `List`, `Form`, and `Calendar` views for WBS
- Timesheets extended with `WBS Phase`

## Example folder structure

```text
odoo-wbs/
|-- docker-compose.yml
|-- config/
|   `-- odoo.conf
`-- custom_addons/
    `-- project_wbs_extension/
```

## Repository

```text
https://github.com/minhhaiabv-wq/odoo_project_wbs_extension
```
