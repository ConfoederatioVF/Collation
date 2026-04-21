global.UI_BrushKeyframes = class extends ve.Class {
	constructor () {
		super();
	}
	
	/**
	 * @returns {ve.Interface}
	 */
	draw () {
		//Return statement
		return new ve.Interface({
			apply_date_range: new ve.Toggle(this.apply_date_range, {
				name: "Apply Date Range",
				onuserchange: (v) => this.disabled = !v,
				tooltip: "Whether to apply brush edits to the given date range."
			}),
			start_date: new ve.Date(main.date, {
				name: "Start Date"
			}),
			end_date: new ve.Date(main.date, {
				name: "End Date"
			})
		}, {
			is_folder: false
		});
	}
}