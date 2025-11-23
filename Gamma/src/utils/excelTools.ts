/* src/utils/excelTools.ts */

export const ExcelTools = {
    // ==================== CELL OPERATIONS ====================

    // 1. modify_cells: Scrie valori sau formule în celule
    modify_cells: async (cells: { [key: string]: string | number }) => {
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

    // 2. read_cells_text: Citește text din celule
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

    // 3. read_cells_values: Citește valori (numerice) din celule
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

    // 4. read_range: Citește un range complet (cu toate datele)
    read_range: async (address: string) => {
        let result: any[][] = [];
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            range.load("values");
            await context.sync();
            result = range.values;
        });
        return result;
    },

    // 5. read_subtable: Returnează array de stringuri
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

    // 6. clear_range: Șterge conținutul unui range
    clear_range: async (address: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            range.clear(Excel.ClearApplyTo.contents);
            await context.sync();
        });
        return "Range cleared";
    },

    // 7. extend: Auto-fill (copiază formule/pattern-uri)
    extend: async (sourceAddr: string, targetAddr: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const sourceRange = sheet.getRange(sourceAddr);
            const finalRange = sheet.getRange(`${sourceAddr}:${targetAddr}`);

            sourceRange.autoFill(finalRange, Excel.AutoFillType.fillDefault);
            await context.sync();
        });
        return "Extended";
    },

    // ==================== WORKSHEET OPERATIONS ====================

    // 8. get_active_sheet: Returnează numele sheet-ului activ
    get_active_sheet: async () => {
        let sheetName = "";
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            sheet.load("name");
            await context.sync();
            sheetName = sheet.name;
        });
        return sheetName;
    },

    // 9. list_sheets: Listează toate sheet-urile
    list_sheets: async () => {
        let sheets: string[] = [];
        await Excel.run(async (context) => {
            const worksheets = context.workbook.worksheets;
            worksheets.load("items/name");
            await context.sync();
            sheets = worksheets.items.map(ws => ws.name);
        });
        return sheets;
    },

    // 10. create_sheet: Creează un sheet nou
    create_sheet: async (name: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.add(name);
            sheet.activate();
            await context.sync();
        });
        return `Sheet '${name}' created`;
    },

    // 11. activate_sheet: Activează un sheet
    activate_sheet: async (name: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getItem(name);
            sheet.activate();
            await context.sync();
        });
        return `Sheet '${name}' activated`;
    },

    // 12. delete_sheet: Șterge un sheet
    delete_sheet: async (name: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getItem(name);
            sheet.delete();
            await context.sync();
        });
        return `Sheet '${name}' deleted`;
    },

    // 13. rename_sheet: Redenumește un sheet
    rename_sheet: async (oldName: string, newName: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getItem(oldName);
            sheet.name = newName;
            await context.sync();
        });
        return `Sheet renamed from '${oldName}' to '${newName}'`;
    },

    // ==================== FORMATTING ====================

    // 14. format_cells: Formatare celule (culori, font, borders)
    format_cells: async (address: string, format: {
        backgroundColor?: string;  // ex: "#FFFF00"
        fontColor?: string;
        fontSize?: number;
        bold?: boolean;
        italic?: boolean;
        horizontalAlignment?: "Left" | "Center" | "Right";
        verticalAlignment?: "Top" | "Center" | "Bottom";
    }) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);

            if (format.backgroundColor) {
                range.format.fill.color = format.backgroundColor;
            }
            if (format.fontColor) {
                range.format.font.color = format.fontColor;
            }
            if (format.fontSize) {
                range.format.font.size = format.fontSize;
            }
            if (format.bold !== undefined) {
                range.format.font.bold = format.bold;
            }
            if (format.italic !== undefined) {
                range.format.font.italic = format.italic;
            }
            if (format.horizontalAlignment) {
                range.format.horizontalAlignment = format.horizontalAlignment as any;
            }
            if (format.verticalAlignment) {
                range.format.verticalAlignment = format.verticalAlignment as any;
            }

            await context.sync();
        });
        return "Format applied";
    },

    // 15. add_border: Adaugă bordură
    add_border: async (address: string, style: "Thin" | "Medium" | "Thick" = "Thin") => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);

            range.format.borders.getItem("EdgeTop").style = style as any;
            range.format.borders.getItem("EdgeBottom").style = style as any;
            range.format.borders.getItem("EdgeLeft").style = style as any;
            range.format.borders.getItem("EdgeRight").style = style as any;

            await context.sync();
        });
        return "Border added";
    },

    // 16. set_number_format: Setează formatul numeric
    set_number_format: async (address: string, format: string) => {
        // Exemple: "0.00", "$#,##0.00", "0%", "dd/mm/yyyy"
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            range.numberFormat = [[format]];
            await context.sync();
        });
        return "Number format applied";
    },

    // ==================== ROWS & COLUMNS ====================

    // 17. insert_rows: Inserează rânduri
    insert_rows: async (startRow: number, count: number) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRangeByIndexes(startRow - 1, 0, count, 1);
            range.insert(Excel.InsertShiftDirection.down);
            await context.sync();
        });
        return `${count} row(s) inserted at row ${startRow}`;
    },

    // 18. delete_rows: Șterge rânduri
    delete_rows: async (startRow: number, count: number) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRangeByIndexes(startRow - 1, 0, count, 1);
            range.delete(Excel.DeleteShiftDirection.up);
            await context.sync();
        });
        return `${count} row(s) deleted from row ${startRow}`;
    },

    // 19. insert_columns: Inserează coloane
    insert_columns: async (column: string, count: number) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(`${column}:${column}`);
            for (let i = 0; i < count; i++) {
                range.insert(Excel.InsertShiftDirection.right);
            }
            await context.sync();
        });
        return `${count} column(s) inserted at ${column}`;
    },

    // 20. delete_columns: Șterge coloane
    delete_columns: async (column: string, count: number) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(`${column}:${column}`);
            for (let i = 0; i < count; i++) {
                range.delete(Excel.DeleteShiftDirection.left);
            }
            await context.sync();
        });
        return `${count} column(s) deleted from ${column}`;
    },

    // 21. auto_fit_columns: Auto-fit lățime coloane
    auto_fit_columns: async (address: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            range.format.autofitColumns();
            await context.sync();
        });
        return "Columns auto-fitted";
    },

    // 22. auto_fit_rows: Auto-fit înălțime rânduri
    auto_fit_rows: async (address: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            range.format.autofitRows();
            await context.sync();
        });
        return "Rows auto-fitted";
    },

    // ==================== CHARTS ====================

    // 23. create_chart: Creează un grafic
    create_chart: async (options: {
        dataRange: string;
        chartType?: string;
        title?: string;
        hasHeaders?: boolean;
        position?: string;
        width?: number;
        height?: number;
    }) => {
        const {
            dataRange,
            chartType = "Column",
            title = "Chart",
            hasHeaders = true,
            position = "D2",
            width = 400,
            height = 300
        } = options;

        console.log("📊 Creating chart with options:", options);

        try {
            await Excel.run(async (context) => {
                const sheet = context.workbook.worksheets.getActiveWorksheet();
                const dataRangeObj = sheet.getRange(dataRange);

                const chart = sheet.charts.add(
                    chartType as any,
                    dataRangeObj,
                    hasHeaders ? Excel.ChartSeriesBy.auto : Excel.ChartSeriesBy.columns
                );

                chart.title.text = title;
                chart.title.visible = true;

                const positionRange = sheet.getRange(position);
                chart.setPosition(positionRange);

                chart.width = width;
                chart.height = height;

                chart.legend.visible = true;
                chart.legend.position = Excel.ChartLegendPosition.right;

                await context.sync();
                console.log("✅ Chart created successfully");
            });

            return "Chart created successfully";
        } catch (error) {
            console.error("❌ create_chart Error:", error);
            throw error;
        }
    },

    // 24. delete_all_charts: Șterge toate graficele
    delete_all_charts: async () => {
        try {
            await Excel.run(async (context) => {
                const sheet = context.workbook.worksheets.getActiveWorksheet();
                const charts = sheet.charts;
                charts.load("items");
                await context.sync();

                charts.items.forEach(chart => chart.delete());
                await context.sync();

                console.log(`✅ Deleted ${charts.items.length} chart(s)`);
            });

            return "All charts deleted";
        } catch (error) {
            console.error("❌ delete_all_charts Error:", error);
            throw error;
        }
    },

    // ==================== TABLES ====================

    // 25. create_table: Creează un tabel Excel
    create_table: async (address: string, tableName: string, hasHeaders: boolean = true) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            const table = sheet.tables.add(range, hasHeaders);
            table.name = tableName;
            await context.sync();
        });
        return `Table '${tableName}' created`;
    },

    // 26. list_tables: Listează toate tabelele
    list_tables: async () => {
        let tables: string[] = [];
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const tablesCollection = sheet.tables;
            tablesCollection.load("items/name");
            await context.sync();
            tables = tablesCollection.items.map(t => t.name);
        });
        return tables;
    },

    // 27. delete_table: Șterge un tabel
    delete_table: async (tableName: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const table = sheet.tables.getItem(tableName);
            table.delete();
            await context.sync();
        });
        return `Table '${tableName}' deleted`;
    },

    // ==================== FORMULAS ====================

    // 28. get_formula: Obține formula dintr-o celulă
    get_formula: async (address: string) => {
        let formula = "";
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            range.load("formulas");
            await context.sync();
            formula = range.formulas[0][0];
        });
        return formula;
    },

    // 29. set_formula: Setează o formulă
    set_formula: async (address: string, formula: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            range.formulas = [[formula]];
            await context.sync();
        });
        return "Formula set";
    },

    // ==================== SORTING & FILTERING ====================

    // 30. sort_range: Sortează un range
    sort_range: async (address: string, columnIndex: number, ascending: boolean = true) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            range.sort.apply([{
                key: columnIndex,
                ascending: ascending
            }]);
            await context.sync();
        });
        return "Range sorted";
    },

    // ==================== FIND & REPLACE ====================

    // 31. find_in_range: Caută text într-un range
    find_in_range: async (address: string, searchText: string) => {
        let results: string[] = [];
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            const foundRanges = range.find(searchText, {
                completeMatch: false,
                matchCase: false
            });

            if (foundRanges) {
                foundRanges.load("address");
                await context.sync();
                results.push(foundRanges.address);
            }
        });
        return results;
    },

    // 32. replace_in_range: Replace text într-un range
    replace_in_range: async (address: string, searchText: string, replaceText: string) => {
        let count = 0;
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            count = range.replaceAll(searchText, replaceText, {
                completeMatch: false,
                matchCase: false
            }).value;
            await context.sync();
        });
        return `${count} replacement(s) made`;
    },

    // ==================== NAMED RANGES ====================

    // 33. create_named_range: Creează un named range
    create_named_range: async (name: string, address: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const range = sheet.getRange(address);
            context.workbook.names.add(name, range);
            await context.sync();
        });
        return `Named range '${name}' created`;
    },

    // 34. get_named_range: Citește dintr-un named range
    get_named_range: async (name: string) => {
        let values: any[][] = [];
        await Excel.run(async (context) => {
            const namedItem = context.workbook.names.getItem(name);
            const range = namedItem.getRange();
            range.load("values");
            await context.sync();
            values = range.values;
        });
        return values;
    },

    // 35. list_named_ranges: Listează toate named ranges
    list_named_ranges: async () => {
        let names: string[] = [];
        await Excel.run(async (context) => {
            const namedItems = context.workbook.names;
            namedItems.load("items/name");
            await context.sync();
            names = namedItems.items.map(item => item.name);
        });
        return names;
    },

    // ==================== PROTECTION ====================

    // 36. protect_sheet: Protejează sheet-ul
    protect_sheet: async (password?: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            sheet.protection.protect({
                allowFormatCells: false,
                allowFormatColumns: false,
                allowFormatRows: false,
                allowInsertColumns: false,
                allowInsertRows: false,
                allowDeleteColumns: false,
                allowDeleteRows: false
            }, password);
            await context.sync();
        });
        return "Sheet protected";
    },

    // 37. unprotect_sheet: Deprotejează sheet-ul
    unprotect_sheet: async (password?: string) => {
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            sheet.protection.unprotect(password);
            await context.sync();
        });
        return "Sheet unprotected";
    },

    // ==================== UTILITIES ====================

    // 38. get_used_range: Obține range-ul folosit
    get_used_range: async () => {
        let address = "";
        await Excel.run(async (context) => {
            const sheet = context.workbook.worksheets.getActiveWorksheet();
            const usedRange = sheet.getUsedRange();
            usedRange.load("address");
            await context.sync();
            address = usedRange.address;
        });
        return address;
    },

    // 39. get_selection: Obține selecția curentă
    get_selection: async () => {
        let address = "";
        let values: any[][] = [];
        await Excel.run(async (context) => {
            const range = context.workbook.getSelectedRange();
            range.load(["address", "values"]);
            await context.sync();
            address = range.address;
            values = range.values;
        });
        return { address, values };
    },

    // 40. calculate: Forțează recalcularea
    calculate: async () => {
        await Excel.run(async (context) => {
            context.workbook.application.calculate(Excel.CalculationType.full);
            await context.sync();
        });
        return "Workbook recalculated";
    }
};
