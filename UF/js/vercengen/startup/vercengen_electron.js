if (!global.ve) global.ve = {};
let electron = require("electron");
let fs = require("fs");
let ipcMain = electron.ipcMain;
let path = require("path");
let readline = require("readline");

//Initialise functions
{
	/**
	 * Utility to read a file line-by-line backwards without loading it all into memory.
	 * This prevents the OOM crash.
	 */
	async function* readLinesBackwards(filePath) {
		const stats = fs.statSync(filePath);
		const fd = fs.openSync(filePath, 'r');
		const bufferSize = 64 * 1024; // 64KB chunks
		const buffer = Buffer.alloc(bufferSize);
		let pos = stats.size;
		let leftover = '';
		
		while (pos > 0) {
			const end = pos;
			pos = Math.max(0, pos - bufferSize);
			const length = end - pos;
			
			fs.readSync(fd, buffer, 0, length, pos);
			let chunk = buffer.toString('utf8', 0, length) + leftover;
			let lines = chunk.split(/\r?\n/);
			
			//The first line in the chunk might be incomplete (split across buffers)
			leftover = lines.shift();
			
			//Yield lines from the end of this chunk (which is newer in the file)
			for (let i = lines.length - 1; i >= 0; i--) {
				yield lines[i];
			}
		}
		if (leftover) yield leftover;
		fs.closeSync(fd);
	}
	
	ve.initialiseIPC = function () {
		ipcMain.on("ontology:initialise", async (event, folderPath) => {
			const webContents = event.sender;
			
			// 1. Sort files descending (YYYY.MM.DD)
			const files = fs.readdirSync(folderPath)
			.filter(f => f.endsWith('.ontology'))
			.sort((a, b) => b.localeCompare(a));
			
			async function* getOntologyBatches() {
				let batch = {};
				let count = 0;
				
				for (const file of files) {
					const filePath = path.join(folderPath, file);
					
					// 2. Process each file backwards line-by-line
					for await (const line of readLinesBackwards(filePath)) {
						if (!line.trim()) continue;
						
						const json_start = line.indexOf('{');
						if (json_start === -1) continue;
						
						const id = line.substring(0, json_start).trim();
						try {
							const kf = JSON.parse(line.substring(json_start));
							kf._saved = true;
							
							if (!batch[id]) batch[id] = [];
							batch[id].push(kf);
							count++;
							
							// Smaller batch size (256) is better for IPC stability
							if (count >= 256) {
								yield batch;
								batch = {};
								count = 0;
							}
						} catch (e) {}
					}
					
					console.log(`Finished reading ${file}`);
				}
				if (Object.keys(batch).length > 0) yield batch;
			}
			
			const currentStream = getOntologyBatches();
			
			const sendNext = async () => {
				const { value, done } = await currentStream.next();
				if (done) {
					webContents.send('ontology-stream-done');
					ipcMain.removeListener('ontology-stream-next', sendNext);
				} else {
					webContents.send('ontology-stream-batch', value);
				}
			};
			
			ipcMain.removeAllListeners('ontology-stream-next');
			ipcMain.on('ontology-stream-next', sendNext);
			sendNext();
		});
	};
}

module.exports = { 
	initialiseIPC: ve.initialiseIPC 
};