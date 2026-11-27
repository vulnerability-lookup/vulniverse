---
icon: lucide/pencil
---

# Using the editor

A short tour for people who write and review vulnerability records. The
editor is the same in the standalone Vulniverse app and when another
application embeds it; only the panels and buttons on offer can differ.

![The editor](../images/screenshots/editor-light.webp#only-light)
![The editor](../images/screenshots/editor-dark.webp#only-dark)

The sidebar on the left switches between the four views of the record
(**Editor**, **Tree**, **Preview**, **Advanced JSON**) and the
**Panels** below them. The arrow at its top collapses it to icons.

## Create a record and choose a profile

In the standalone app, click **Create new record** on the records page,
then pick a profile:

| Profile | What it is |
| --- | --- |
| **CVE** | A standard CVE Record Format 5.2.0 record. |
| **GCVE** | A CVE record extended with the GCVE-BCP-05 1.7 `x_gcve` extension. |
| **OSV** | An Open Source Vulnerability (OSV) 1.9.2 record. |

The profile decides which fields the form offers and which schema the
record is checked against. The first **Save** creates the record. To try
the editor without an account, open `/try`: nothing is saved there.

## The form

The **Editor** view groups the fields in tabs, such as *Metadata*,
*Summary*, *Affected products*, *Severity* and *References* (the tabs
depend on the profile). Lists are shown as cards with **+ Add** and
**Remove**; the number of entries follows the list's title. A list with
one entry opens it, a longer list starts closed, and **Expand all** /
**Collapse all** opens or closes every card at once.

Versions of an affected product have their own editor. Each entry is a
**Single version** or a **Range** (*From version*, *Up to* with `<` or
`≤`, and status changes within the range). Some fields, such as the
version type, suggest values as you type, but any text is allowed.
Next to a CVSS vector, **Calculate** opens a CVSS calculator (versions
2, 3.x and 4) that shows the score for each choice before you **Apply**
it.

## The record tree

![The record tree](../images/screenshots/tree-light.webp#only-light)
![The record tree](../images/screenshots/tree-dark.webp#only-dark)

**Tree** draws the whole record as a graph. Click a circle to open or
close a field, and click a name to jump to that field in the form (the
right tab and card open). The search box finds names and values; Enter
and the arrows step through the matches. Missing required fields, changed
fields and fields with errors are marked.

## Preview

![The preview](../images/screenshots/preview-light.webp#only-light)
![The preview](../images/screenshots/preview-dark.webp#only-dark)

**Preview** is a read-only rendering of the record as currently edited,
close to how readers will see it. Use it for a last check before saving
or publishing.

## Advanced JSON

**Advanced JSON** shows the complete record as JSON. In **Edit** you can
change or paste the whole record; nothing changes until you click
**Apply JSON**, and **Discard edits** throws your edits away.
**Changes** compares the record as saved with the record now, line by
line: removed lines in red, added lines in blue.

![The JSON changes view](../images/screenshots/json-changes-light.webp#only-light)
![The JSON changes view](../images/screenshots/json-changes-dark.webp#only-dark)

## Unsaved changes

Everything you change is marked until you save. A changed field gets a
bar at its left edge. A new card gets a **New** badge, and a closed card
says how many fields inside it changed. An entry you removed stays
visible under its list as **Removed**, with **Restore** to put it back.

![Unsaved changes](../images/screenshots/changes-light.webp#only-light)
![Unsaved changes](../images/screenshots/changes-dark.webp#only-dark)

The header shows a badge such as *2 unsaved changes*. Click it for the
list of every change, with the old and the new value. **Show** takes you
to the field, **Undo** reverts that one change, and **Undo all** goes back
to the last saved version.

## Save, Validate, Publish

**Validate** checks the record against its schema without saving. Errors
are listed with their field; click one to go to it. **Save** stores the
record as it is, even if it's incomplete. **Reload** loads the saved
version again.

A record starts as a **Draft** (badge in the header). **Publish** saves it
and marks it as published; **Revert to draft** turns it back into a draft.
Applications that embed the editor may have no drafts and hide these
buttons. Depending on the profile and the host, the header also offers
**Reject** (turn the record into a rejected one, with a reason) and
**Delete**.

## Panels

Panels are extra tools below the views in the sidebar. Which ones you see
depends on the server: in the standalone app they are switched on in
[Configuration](../setup/config.md#panels-actions), and an embedding
application chooses its own. A panel the server can't support says so
instead of showing its tools.

### Templates

A template is a set of field values you reuse, for example the vendor,
product and CPEs of a product you write many records for. **Create a new
template** from paths and values, or use **Capture fields from the
current record** to pick filled-in fields. **Apply** writes a template's
values into the current record. **Export** saves one template as a JSON
file and **Import template…** loads one, for example on another server.
Templates belong to one profile.

### Record Quality

![Record Quality](../images/screenshots/quality-light.webp#only-light)
![Record Quality](../images/screenshots/quality-dark.webp#only-dark)

**Record Quality** scores the record from 0 to 100, with a grade and the
points per area and per check. It scores in the browser and updates
with every edit. The method is Vulnerability-Lookup's assigner
scorecard.

### Patch2Vuln

**Patch2Vuln** analyses a security fix and drafts the vulnerability
information from it. Give one or more **GitHub commit URLs** (one per
line, all for the same vulnerability) or upload **Patch files**
(`.patch`, `.diff`). Vendor, product, versions and a package URL are
optional context; **Additional instructions** let you tell the model what
the patch doesn't show or what to focus on.

**Analyze patches** starts the job. It runs in the background: you can
switch to other views, and a notification says when it's done. Then tick
the fields you want and click **Apply selected fields**; they replace the
current values, while identifiers and publication data are kept. Always
review the result before publishing.

#### Several commits at once

In the standalone app, **Patch2Vuln** in the top bar analyses up to 50
vulnerabilities in one batch, one record each. Give the batch a name,
choose the record format and paste the GitHub commit URLs, one line per
vulnerability. When several commits fix the same vulnerability, put them
on the same line, separated by spaces (up to 5); they're analysed
together. Below the field, a preview lists the vulnerabilities as they
will be analysed and marks lines that can't be, such as URLs that aren't
GitHub commits. The batch belongs to your organisation: your colleagues
see it too.

The batch page lists each vulnerability with its commits and the title
Patch2Vuln generated, and updates itself while analyses run.

- **Review** opens the generated record in the editor as a new record.
  Nothing is stored until you save it; then the batch shows
  **Open record**.
- **Dismiss** marks a commit you don't want a record for; **Restore**
  undoes it.
- **Delete batch** cancels the analyses still running. Records already
  created stay.

Results are kept in Vulniverse once an analysis has finished, so a batch
can be reviewed over several days even though Patch2Vuln deletes them.

### Vulnerability-Lookup and CVE Program

These two panels publish the record to a Vulnerability-Lookup instance or
to the CVE Program. They need a server listed in the configuration and,
in the standalone app, your own CNA credentials (the CNA credentials
page).

- For a new vulnerability, **Reserve a GCVE ID** (Vulnerability-Lookup)
  or **Reserve a CVE ID** (CVE Program).
- If the vulnerability already has an ID there, enter it and click
  **Link**: the record takes over its status, and its content once
  published.
- Then **Publish to …** sends the record; later, **Publish update** sends
  your changes. **Reject…** rejects the ID with a reason.
- Once published, the panel compares your record with the published
  version. **Show differences** lists the fields that differ; **Use VL's**
  / **Use CVE's** takes one upstream value, **Use all from …** takes them
  all.
- **Check with …** fetches the current state, and **Stop tracking**
  removes the link (the ID stays upstream).

## Download and Tutorial

**Download** saves the record as **JSON**, as an **HTML page**, or as a
**PDF** through the browser's print dialog. **Tutorial** starts a short
guided tour of the editor: the record, the actions, the views, tabs,
fields, validation, the tree, the preview and Advanced JSON. Both are
buttons in the header and can be switched off in
[Configuration](../setup/config.md#panels-actions).
