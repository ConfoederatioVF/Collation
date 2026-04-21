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
			start_date: new ve.Date((this.start_date) ? this.start_date : main.date, {
				name: "Start Date",
				onuserchange: (v) => this.start_date = v
			}),
			end_date: new ve.Date((this.end_date) ? this.end_date : main.date, {
				name: "End Date",
				onuserchange: this.end_date = v
			})
		}, {
			is_folder: false
		});
	}
}