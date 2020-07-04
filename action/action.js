const { spawn } = require('child_process');

function validate() {
    const python = spawn('python3', ['action.py']);
    python.stdout.on('data', function (output) {
        console.log(output.toString())
    });
    python.on('close', (code) => {
        console.log(code)
        return code
    });
}

return validate()