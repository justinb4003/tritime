import pandas as pd
import lib.tritime as tt


def export_to_excel(filename='report.xlsx'):
    # First get a list of every user in the system
    badges = tt.get_badges()
    # Create some empty lists to hold the data that we'll put into a DataFrame
    bcol, dcol, tin, tout, tdiff = [], [], [], [], []
    # Now let's loop through everybody in the system.
    for badge_num, badge in badges.items():
        dn = badge['display_name']
        # Grab their punnch in/out data one by one
        punch_data = tt.read_punches(badge_num)
        # Now for every punch in/out pair, let's add it to our lists
        for p in punch_data:
            if 'ts_in' not in p or 'ts_out' not in p:
                continue  # And flag as an error?
            bcol.append(badge_num)
            dcol.append(dn)
            tin.append(p['ts_in'])
            tout.append(p['ts_out'])
            tdiff.append(p['duration'])

    # With all the data in lists, let's create a DataFrame
    tdf = pd.DataFrame({'badge': bcol, 'display_name': dcol,
                        'time_in': tin, 'time_out': tout, 'duration': tdiff})

    # Now we 'cast' the data to the correct types; fixing datetime here
    tdf['time_in'] = pd.to_datetime(tdf['time_in'])
    tdf['time_out'] = pd.to_datetime(tdf['time_out'])
    # Now let's make a new column that tells of what week of the year it is
    tdf['week_number'] = tdf['time_in'].dt.isocalendar().week
    # And because nobody likes to think of dates by week number of year (except
    # perhaps farmers), let's make a new column that tells us the start of the week
    # as a date.
    tdf['sow'] = (
        tdf['time_in'] - pd.to_timedelta(tdf['time_in'].dt.dayofweek, unit='d')
    ).dt.date
    tdf['year'] = tdf['time_in'].dt.isocalendar().year
    tdf.to_csv('test.csv', index=False)
    tdf.to_parquet('test.parquet', index=False)
    udf = tdf[['badge', 'display_name']].drop_duplicates()
    # Now use the raw data to create a DataFrame that has the total time worked
    # for each user for every week of the year.
    wdf = (
        tdf.drop(['display_name', 'time_in', 'time_out'], axis=1)
        .groupby(['badge', 'year', 'week_number', 'sow'])
        .sum()
    ).reset_index()

    # Now let's merge the two DataFrames together to get a final DataFrame that
    # makes for a decent report
    merged = pd.merge(wdf, udf, on=['badge'], how='left')
    merged['duration_hours'] = merged['duration'] / 3600
    # Last we 'pivot' the data so that the weeks are new each a column
    finaldf = (
        merged.pivot(index='display_name',
                     columns='sow',
                     values='duration_hours').fillna(0).reset_index(level=0)
    )
    finaldf.to_excel(filename, index=False)
    print('export complete')
