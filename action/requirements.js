const { spawn } = require('child_process');
const core = require('@actions/core');
console.log("Oh boy this is dirty")

function install() {
    const requirements = spawn('python3', ['-m', 'pip', 'install', 'setuptools', 'wheel'])
    requirements.stdout.on('data', function (output) {
        console.log(output.toString())
    });
    requirements.on('close', (code) => {
        console.log(code)
        if (code !== 0) {
            core.setFailed("Could not install requirements");
        }
        installRequirements()
    });
}

function installRequirements() {
    const requirements = spawn('python3', ['-m', 'pip', 'install', '-r', 'requirements.txt'])
    requirements.stdout.on('data', function (output) {
        console.log(output.toString())
    });
    requirements.on('close', (code) => {
        if (code !== 0) {
            core.setFailed("Could not install requirements");
        }
    });
}

install()