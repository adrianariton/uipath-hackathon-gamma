/* src/utils/excelTools.ts */

export const ExcelTools = {
  // 1. modify_cells: Scrie valori sau formule
  modify_cells: async (cells: { [key: string]: string | number }) => {
    // [DEBUG] Vedem exact ce primim de la App.tsx
    console.log("👉 ExcelTools.modify_cells called with:", cells);

    if (!cells || Object.keys(cells).length === 0) {
        console.warn("⚠️ modify_cells received empty data!");
        return "Error: No cells data provided to write.";
    }

    try {
        await Excel.run(async (context) => {
          const sheet = context.workbook.worksheets.getActiveWorksheet();
          
          for (const [address, value] of Object.entries(cells)) {
            console.log(`📝 Writing value '${value}' into cell '${address}'`);
            
            const range = sheet.getRange(address);
            range.values = [[value]]; 
          }
          await context.sync();
          console.log("✅ Excel.sync() completed successfully.");
        });
        return "Success";
    } catch (error) {
        console.error("❌ ExcelTools Error:", error);
        throw error;
    }
  },

  // 2. read_subtable: Returnează array de stringuri
  read_subtable: async (col1: string, col2: string, row1: number, row2: number) => {
    let result: string[] = [];
    await Excel.run(async (context) => {
      const sheet = context.workbook.worksheets.getActiveWorksheet();
      
      const address = `${col1}${row1}:${col2}${row2}`;
      const range = sheet.getRange(address);
      range.load("text");
      await context.sync();

      result = range.text.map((row: string[]) => row.join(" "));
    });
    return result;
  },

  // 3. read_cells_text: FIXAT ȘI OPTIMIZAT
  read_cells_text: async (addresses: string[]) => {
    let result: { [key: string]: string } = {};
    if (addresses.length === 0) return result;

    await Excel.run(async (context) => {
      const sheet = context.workbook.worksheets.getActiveWorksheet();
      let trackedRanges: { addr: string; range: Excel.Range }[] = [];

      for (const addr of addresses) {
          const r = sheet.getRange(addr);
          r.load("text");
          trackedRanges.push({ addr: addr, range: r });
      }

      await context.sync();

      for (const item of trackedRanges) {
          result[item.addr] = item.range.text[0][0];
      }
    });
    return result;
  },

  // 4. read_cells_values: FIXAT ȘI OPTIMIZAT
  read_cells_values: async (addresses: string[]) => {
    let result: { [key: string]: any } = {};
    if (addresses.length === 0) return result;

    await Excel.run(async (context) => {
      const sheet = context.workbook.worksheets.getActiveWorksheet();
      let trackedRanges: { addr: string; range: Excel.Range }[] = [];

      for (const addr of addresses) {
          const r = sheet.getRange(addr);
          r.load("values");
          trackedRanges.push({ addr: addr, range: r });
      }

      await context.sync();

      for (const item of trackedRanges) {
          result[item.addr] = item.range.values[0][0];
      }
    });
    return result;
  },

  // 5. extend: Auto-fill
  extend: async (sourceAddr: string, targetAddr: string) => {
    await Excel.run(async (context) => {
      const sheet = context.workbook.worksheets.getActiveWorksheet();
      const sourceRange = sheet.getRange(sourceAddr);
      const finalRange = sheet.getRange(`${sourceAddr}:${targetAddr}`);
      
      sourceRange.autoFill(finalRange, Excel.AutoFillType.fillDefault);
      await context.sync();
    });
    return "Extended";
  }
};