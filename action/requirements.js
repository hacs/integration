const { spawn } = require('child_process');
console.log("Oh boy this is dirty")

function run() {
    const requirements = spawn('python3', ['-m', 'pip', 'install', 'setuptools', 'wheel'])
    requirements.stdout.on('data', function (output) {
        console.log(output.toString())
    });
    requirements.on('close', (code) => {
        console.log(code)
        if (code !== 0) {
            return code
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
        return code
    });
}

return run()