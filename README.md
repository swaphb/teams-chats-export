
# teams-chats-export

Script to export your Microsoft Teams [chats](https://learn.microsoft.com/en-us/graph/api/resources/chat?view=graph-rest-1.0)
and view them as .html files. Chats are conversations separate from those on Teams channels. These include one-on-one chats,
group chats, and meeting chats.

## Design Goals

Unlike similar export tools, this does NOT require using Windows or PowerShell. The only requirement is Python.

Originally you did not need to register an application with the Microsoft Identity Platform or Microsoft Entra ID,
but as of Sept 9th, 2024, [that is no longer the case](https://pnp.github.io/blog/post/changes-pnp-management-shell-registration/).

This was created specifically in response to a new retention policy for Teams chats
implemented at my workplace.

## Instructions


### Create an Entra ID application if needed

You'll need either an existing Entra ID application with permissions to access Teams,
or you'll need to create a new one.

If you have an existing application, find its application/client ID.

If you need to create one, the steps are [here](https://pnp.github.io/powershell/articles/registerapplication.html#manually-create-an-app-registration-for-interactive-login).
In a nutshell:

- Log into https://entra.microsoft.com/
- Navigate to Applications -> App Registrations
- Click "New registration" and give it a name like "Teams API"
- Navigate to Authentication for the new app
- Click "Add a platform" and select "Mobile and desktop applications"
- Enter the following custom redirect URI: http://localhost:8400
- Save your changes

You don't need to configure specific API permissions. The default "User.Read" delegated
permission will give users access to their own Teams data.

Copy your new application's "Application (client) ID" from the Overview screen. It should look
something like "31359c7f-bd7e-475c-86db-fdb8c937548e" (that's the ID for the old built-in
PnP Management Shell Entra App that Microsoft has disabled, it won't work).

### Install the script

Do this once:

```sh
# set up and activate a virtual environment
python -m venv teams-chats-export-env
. ./teams-chats-export-env/bin/activate

# install dependencies
pip install -r requirements.txt
```

Alternatively, with Nix and flakes enabled, enter the pinned development shell and
install the Python dependencies into a virtual environment:

```sh
nix develop
python -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
```

On later visits, run `nix develop` and `. .venv/bin/activate`. The flake pins
Python through `flake.lock`; installing the Python packages requires network
access. The versions explicitly pinned in `requirements.txt` are installed by
pip, while transitive dependencies may change over time.

Run the tests from the activated environment:

```sh
python -m unittest discover -s tests -v
```

### Dependency updates

After these configurations are merged into the fork's default branch, Dependabot
checks the direct Python dependencies and GitHub Actions weekly and opens grouped
pull requests against `main`. A separate weekly workflow updates `flake.lock` and
opens a pull request against `main`; it can also be run manually from the Actions
tab. The repository's Actions settings must allow GitHub Actions to create pull
requests. Pull requests created with `GITHUB_TOKEN` do not automatically trigger
other Actions workflows; close and reopen the flake update PR to run them.
Transitive Python dependencies are resolved by pip at installation time and are
not locked by this configuration.

### Run the script

To archive your chats:

```sh
# activate the virtual env every time you want to use it
. ./teams-chats-export-env/bin/activate

# run two steps to download and generate html files in the './archive' directory
# to use another dir, set --output-dir=/some/other/dir

# step one: download
# replace value for CLIENT_ID with your own ID
CLIENT_ID="31359c7f-bd7e-475c-86db-fdb8c937548e" python teams_chats_export.py download

# step two: generate html files
python teams_chats_export.py generate_html
```

The download step will open a browser window for you to authenticate.

Files will be written to directories named `data` and `html` within the output directory.
The `html` directory includes an `index.html` containing a listing of the chats.

You can run the download step on your archive directory periodically to update the data.
Previously downloaded data, including anything deleted on Teams since the last time you
ran the script, will be retained in the directory. (If you want to be really safe, consider
making a backup copy of the archive directory from time to time.)

Only "new" messages are downloaded, but this logic may not catch certain edge cases.
If you're missing messages or you don't see edits, or you just want to be absolutely sure
you're downloading everything, run `python teams_chats_export.py download --force`
to re-process all the available messages on Teams.

Images hosted outside of Teams (GIFs, stickers, images linked from other sites) are
rendered as links by default, so opening an exported chat doesn't contact those servers
(which would reveal your IP address and fire any tracking pixels). To display them inline
instead, run `python teams_chats_export.py generate_html --remote-images`. Images hosted
on Teams are always embedded in the .html files.

### Choosing which chats to export

By default every chat is exported. To export only some of them, pass `--chats-file`
with a text file of wildcard patterns, one per line:

```text
# lines starting with # are comments; blank lines are ignored
Project Phoenix*
*Alice Smith*
19:0123abcd@thread.v2

# a leading ! excludes chats, even ones matched above
!*Lunch*
```

Each pattern is matched case-insensitively against the chat's name and its ID. `*`
matches any run of characters and `?` matches one character. A chat's name is its
topic, or for chats without a topic, a comma-separated list of its members in
alphabetical order. That member list changes when people join or leave, so use the ID
for those chats. If the file contains only `!` patterns, every other chat is exported.
Topics containing `/` match both the original topic and the name displayed by
`list_chats`, where `/` is replaced by `_`. Square brackets match literally.

To see each chat's name and ID, run:

```sh
CLIENT_ID="..." python teams_chats_export.py list_chats
```

`list_chats` also accepts `--chats-file`, so you can check which chats a file selects
before downloading. Then pass the same file to both steps:

```sh
CLIENT_ID="..." python teams_chats_export.py download --chats-file chats.txt
python teams_chats_export.py generate_html --chats-file chats.txt
```

Filtering doesn't delete anything already in the archive directory. Chats downloaded
earlier stay in `data`, and `generate_html` without `--chats-file` still renders them.

If you want to customize the html outputs, edit the files in `templates/` to your
liking and re-run the generate_html step above.

## Limitations

- Doesn't render reactions in the .html

- Not all attachment types are handled properly. (Meta)data for unhandled attachments
  is written directly to the .html file with the string prefix "Attachment (raw data):"
