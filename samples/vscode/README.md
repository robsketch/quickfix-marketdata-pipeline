# kdb Visual Studio Code Extension

## Introduction
This guide shows you how to query kdb Insights using the KX [kdb Visual Studio Code extension](https://marketplace.visualstudio.com/items?itemName=KX.kdb).

## Pre-requisite
* The kdb Insights is running
* [Visual Studio Code](https://code.visualstudio.com/) is installed
* kdb Visual Studio Code extension is installed

## Walkthrough
The following steps describe how to start a [managed q session](https://github.com/KxSystems/kx-vscode#managed-q-session) and use it to execute a q script which queries kdb Insights using the [`getData` API](https://code.kx.com/insights/1.8/api/database/query/get-data.html).
1. Launch VS Code
2. Press the KX button on the Activity Bar (far left-hand side)
3. In the KX Side Bar press the "Add Connection" button within the Connections context menu. You may need to press the <kbd>…</kbd> button if the "Add Connection" button is not visible.
4. Select "Enter a kdb endpoint" as the connection type
5. Enter `local` as the connection name
6. Enter `localhost` as the hostname
7. Enter a free port e.g. 5001
8. Right click on the new connection in the Connections context menu and select "Start q process"
9. Right click on the connection again and select "Connect server"
10. Open the `sample.q` file
11. Right click on the Editor and select "Execute Entire File"
12. The results (i.e. taxi table data) should be displayed in the "kdb Results" section of the Status Bar

## Links
* [Visual Studio Code User Interface | code.visualstudio.com](https://code.visualstudio.com/docs/getstarted/userinterface)
