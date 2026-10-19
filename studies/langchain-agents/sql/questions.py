"""Questions for the text-to-SQL agent, each with a gold SQL query written by hand.

The reference answer is not typed in: `build_dataset.py` runs each gold query on the Chinook
database and records the values a correct answer must contain. Questions were written before any
agent run and span three levels, so the set is neither trivial nor unfair:

- easy: one table, one filter or count;
- medium: one or two joins with an aggregate;
- hard: three or more joins, a date range, a ranking, a ratio, or an "only/never" condition.

Each gold query returns one row, or a short fixed list, so "contains every value" is a fair
check. Money is rounded to two decimals in the gold query and the question asks for the same.
`cols` names the result columns whose values the answer must contain.
"""

Q = [
    # easy
    ("easy", "How many customers are from Brazil?",
     "SELECT COUNT(*) FROM Customer WHERE Country='Brazil'", None),
    ("easy", "How many tracks are longer than 10 minutes?",
     "SELECT COUNT(*) FROM Track WHERE Milliseconds > 600000", None),
    ("easy", "What is the title of the album with AlbumId 100?",
     "SELECT Title FROM Album WHERE AlbumId=100", None),
    ("easy", "How many employees report directly to the General Manager?",
     "SELECT COUNT(*) FROM Employee WHERE ReportsTo=(SELECT EmployeeId FROM Employee WHERE Title='General Manager')", None),
    ("easy", "In how many different countries do the store's customers live?",
     "SELECT COUNT(DISTINCT Country) FROM Customer", None),
    ("easy", "What is the total of all invoices issued in 2011, rounded to two decimals?",
     "SELECT ROUND(SUM(Total),2) FROM Invoice WHERE strftime('%Y',InvoiceDate)='2011'", None),
    # medium
    ("medium", "Which artist has the most albums in the store, and how many albums do they have?",
     "SELECT ar.Name, COUNT(*) c FROM Album al JOIN Artist ar USING(ArtistId) GROUP BY ar.ArtistId ORDER BY c DESC LIMIT 1", None),
    ("medium", "Which genre has the most tracks, and how many tracks is that?",
     "SELECT g.Name, COUNT(*) c FROM Track t JOIN Genre g USING(GenreId) GROUP BY g.GenreId ORDER BY c DESC LIMIT 1", None),
    ("medium", "Which country's customers spent the most in total, and what was that total, rounded to two decimals?",
     "SELECT BillingCountry, ROUND(SUM(Total),2) s FROM Invoice GROUP BY BillingCountry ORDER BY s DESC LIMIT 1", None),
    ("medium", "Which customer has spent the most money in total? Give their full name and the total rounded to two decimals.",
     "SELECT c.FirstName||' '||c.LastName, ROUND(SUM(i.Total),2) s FROM Invoice i JOIN Customer c USING(CustomerId) GROUP BY c.CustomerId ORDER BY s DESC LIMIT 1", None),
    ("medium", "Which sales support agent's customers generated the most invoice revenue? Give the agent's full name and the revenue rounded to two decimals.",
     "SELECT e.FirstName||' '||e.LastName, ROUND(SUM(i.Total),2) s FROM Invoice i JOIN Customer c USING(CustomerId) JOIN Employee e ON e.EmployeeId=c.SupportRepId GROUP BY e.EmployeeId ORDER BY s DESC LIMIT 1", None),
    ("medium", "How many tracks are in the playlist named 'Grunge'?",
     "SELECT COUNT(*) FROM PlaylistTrack pt JOIN Playlist p USING(PlaylistId) WHERE p.Name='Grunge'", None),
    ("medium", "What is the average length of a track in the 'Jazz' genre, in whole seconds (rounded down)?",
     "SELECT CAST(AVG(Milliseconds)/1000 AS INT) FROM Track JOIN Genre USING(GenreId) WHERE Genre.Name='Jazz'", None),
    ("medium", "Which media type has sold the most units (invoice line quantities), and how many units?",
     "SELECT m.Name, SUM(il.Quantity) q FROM InvoiceLine il JOIN Track t USING(TrackId) JOIN MediaType m USING(MediaTypeId) GROUP BY m.MediaTypeId ORDER BY q DESC LIMIT 1", None),
    # hard
    ("hard", "Which artist earned the most revenue from track sales, and how much, rounded to two decimals?",
     "SELECT ar.Name, ROUND(SUM(il.UnitPrice*il.Quantity),2) s FROM InvoiceLine il JOIN Track t USING(TrackId) JOIN Album al USING(AlbumId) JOIN Artist ar USING(ArtistId) GROUP BY ar.ArtistId ORDER BY s DESC LIMIT 1", None),
    ("hard", "Which genre brought in the most revenue from customers in the USA, and how much, rounded to two decimals?",
     "SELECT g.Name, ROUND(SUM(il.UnitPrice*il.Quantity),2) s FROM InvoiceLine il JOIN Invoice i USING(InvoiceId) JOIN Track t USING(TrackId) JOIN Genre g USING(GenreId) WHERE i.BillingCountry='USA' GROUP BY g.GenreId ORDER BY s DESC LIMIT 1", None),
    ("hard", "How many tracks have never been sold?",
     "SELECT COUNT(*) FROM Track WHERE TrackId NOT IN (SELECT TrackId FROM InvoiceLine)", None),
    ("hard", "How many artists have no albums in the store?",
     "SELECT COUNT(*) FROM Artist WHERE ArtistId NOT IN (SELECT ArtistId FROM Album)", None),
    ("hard", "In which month of 2012 was revenue highest? Give the month as YYYY-MM and the revenue rounded to two decimals.",
     "SELECT strftime('%Y-%m',InvoiceDate) m, ROUND(SUM(Total),2) s FROM Invoice WHERE strftime('%Y',InvoiceDate)='2012' GROUP BY m ORDER BY s DESC LIMIT 1", None),
    ("hard", "Which album has the highest number of distinct customers who bought at least one of its tracks? Give the album title and that number of customers.",
     "SELECT al.Title, COUNT(DISTINCT i.CustomerId) c FROM InvoiceLine il JOIN Invoice i USING(InvoiceId) JOIN Track t USING(TrackId) JOIN Album al USING(AlbumId) GROUP BY al.AlbumId ORDER BY c DESC LIMIT 1", None),
    ("hard", "How many customers have bought tracks from at least 10 different genres?",
     "SELECT COUNT(*) FROM (SELECT i.CustomerId FROM InvoiceLine il JOIN Invoice i USING(InvoiceId) JOIN Track t USING(TrackId) GROUP BY i.CustomerId HAVING COUNT(DISTINCT t.GenreId) >= 10)", None),
    ("hard", "What share of all invoice revenue came from customers in Germany, France and the United Kingdom combined? Give the percentage rounded to one decimal.",
     "SELECT ROUND(100.0*SUM(CASE WHEN BillingCountry IN ('Germany','France','United Kingdom') THEN Total ELSE 0 END)/SUM(Total),1) FROM Invoice", None),
    ("hard", "Not counting the General Manager, which employee has the most people reporting to them, directly or through others? Give their full name.",
     "WITH RECURSIVE r(boss, emp) AS (SELECT ReportsTo, EmployeeId FROM Employee WHERE ReportsTo IS NOT NULL UNION ALL SELECT e.ReportsTo, r.emp FROM Employee e JOIN r ON e.EmployeeId=r.boss WHERE e.ReportsTo IS NOT NULL) SELECT e.FirstName||' '||e.LastName FROM r JOIN Employee e ON e.EmployeeId=r.boss WHERE e.Title <> 'General Manager' GROUP BY r.boss ORDER BY COUNT(*) DESC LIMIT 1", None),
    ("hard", "Which playlist contains the most tracks from the 'Rock' genre, and how many Rock tracks does it contain? Count each track once.",
     "SELECT p.Name, COUNT(DISTINCT t.TrackId) c FROM PlaylistTrack pt JOIN Playlist p USING(PlaylistId) JOIN Track t USING(TrackId) JOIN Genre g USING(GenreId) WHERE g.Name='Rock' GROUP BY p.PlaylistId ORDER BY c DESC LIMIT 1", None),
]
