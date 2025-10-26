const ContractValidator = require('./src/tests/contracts/contractValidator.js');

async function test() {
    const validator = new ContractValidator('http://localhost:8000', 'http://localhost:8000');
    try {
        const report = await validator.validateAllContracts();
        validator.printSummary(report);
        process.exit(report.summary.errors > 0 ? 1 : 0);
    } catch (error) {
        console.error('Error:', error.message);
        console.error('Stack:', error.stack);
        process.exit(1);
    }
}

test();
