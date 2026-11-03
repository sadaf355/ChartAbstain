# Audit report

- rows in adapted file: 1966 (original 1970)
- matched to answer key: 1966 (100.0%); unmatched 0; duplicate ids 0
- answers that fail the checker: 482 (24.5% of matched)
-   wrong content: 223 (11.3%); of which answerable questions flipped to abstain: 83
-   right meaning, broken wording or format: 259 (13.2%)
- abstention rows that fail the checker: 82 of 411 (labels stripped: 82)
- correct answers carrying a wrong Type label: 1146 of 1484
- enhanced rows kept after repair: 1484
- rows the platform dropped, restored from original: 4
- rows in repaired dataset: 1970

## Damage categories (answers that fail the checker)

| category | rows | share of matched |
|---|---|---|
| format: trend reworded (right direction) | 177 | 9.0% |
| content: wrong number or name | 130 | 6.6% |
| content: answerable question flipped to abstain | 83 | 4.2% |
| format: abstention kept, labels stripped | 82 | 4.2% |
| content: trend wrong direction or unclear | 10 | 0.5% |

## Failure rate by question type

| type | failing | total | rate |
|---|---|---|---|
| abstain | 82 | 410 | 20% |
| axis | 2 | 21 | 10% |
| diff | 2 | 220 | 1% |
| max | 18 | 238 | 8% |
| min | 18 | 224 | 8% |
| pct | 26 | 220 | 12% |
| rank | 42 | 210 | 20% |
| share | 101 | 193 | 52% |
| trend | 187 | 197 | 95% |
| unit | 4 | 33 | 12% |

## Type labels found in the adapted answers (required: computed, abstain)

`abstain` 427, `bar chart` 320, `line chart` 247, `bar_chart` 155, `ranking` 138, `numeric` 115, `calculation` 89, `(none)` 63, `line_chart` 63, `single` 54

## Wrong answers (original vs adapted)

**A-2706**
Original: Answer: 41.3% of the total | Reason: Primary is 946 out of a total of 2291 in 2015. | Type: computed
Adapted: Answer: 41.0% | Reason: In 2015, Primary enrollment was 946 out of a total of 2291 (946+211+1134), which equals approximately 41.0%. | Type: number

**A-2766**
Original: Answer: 46.9% of the total | Reason: ICU is 53.7 out of a total of 114.5 in Week 3. | Type: computed
Adapted: Answer: Cannot be determined from this chart. | Reason: The data provides occupancy percentages for each ward individually, not the raw bed counts needed to calculate ICU's share of the total occupancy. | Type: abstain

**A-2220**
Original: Answer: Cannot be determined from this chart. | Reason: The chart shows only bed occupancy by ward (percent). It does not show number of employees. | Type: abstain
Adapted: Cannot be determined from this chart. | The chart displays bed occupancy percentages, not the number of employees. | abstain

**A-0673**
Original: Answer: HR decreased | Reason: HR went from 16.1 in Q1 FY24 to 12.0 in Q3 FY25. | Type: computed
Adapted: Answer: Down | Reason: HR expenses decreased from 16.1 INR lakh in Q1 FY24 to 12.0 INR lakh in Q3 FY25. | Type: line_chart

**A-2421**
Original: Answer: Primary increased | Reason: Primary went from 695 in 2018 to 715 in 2021. | Type: computed
Adapted: Answer: Increase | Reason: Primary enrollment rose from 695 students in 2018 to 715 students in 2021. | Type: Bar chart

## Bad Type labels (adapted)

**A-2401**
Answer: The South region's sales increased by approximately 19.65% between January and April. | Reason: The sales in January were 103.8 INR lakh, and in April, they were 124.2 INR lakh; the percentage change is calculated as ((124.2 - 103.8) / 103.8) * 100. | Type: Calculation

**A-0764**
Answer: Primary | Reason: In 2021, Primary enrollment was 1500 students, which is higher than Secondary enrollment of 990 students. | Type: bar chart

**A-0348**
Answer: 308 | Reason: In 2022, Senior enrollment was 679 and Middle enrollment was 371, so the difference is 679 - 371 = 308. | Type: bar_chart
