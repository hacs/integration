const { spawn } = require('child_process');

// Install requirements
const requirements = spawn('python3', ['-m', 'pip', 'install', '-r', 'requirements.txt'])
requirements.stdout.on('data', function (output) {
    console.log(output.toString())
});
requirements.on('close', (code) => {
    if (code !== 0) {
        return code
    }
    // Run the validation
    const python = spawn('python3', ['action.py']);
    python.stdout.on('data', function (output) {
        console.log(output.toString())
    });
    python.on('close', (code) => {
        return code
    });
});

