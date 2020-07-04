const { spawn } = require('child_process');
const core = require('@actions/core');

function validate() {
    const python = spawn('python3', ['action.py']);
    python.stdout.on('data', function (output) {
        console.log(output.toString())
    });
    python.on('close', (code) => {
        if (code !== 0) {
            core.setFailed("Could not install requirements");
        }
    });
}

validate()