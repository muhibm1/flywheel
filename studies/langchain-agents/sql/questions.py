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
    (
        "easy",
        "How many customers are from Brazil?",
        "SELECT COUNT(*) FROM Customer WHERE Country='Brazil'",
        None,
    ),
    (
        "easy",
        "How many tracks are longer than 10 minutes?",
        "SELECT COUNT(*) FROM Track WHERE Milliseconds > 600000",
        None,
    ),
    (
        "easy",
        "What is the title of the album with AlbumId 100?",
        "SELECT Title FROM Album WHERE AlbumId=100",
        None,
    ),
    (
        "easy",
        "How many employees report directly to the General Manager?",
        "SELECT COUNT(*) FROM Employee WHERE ReportsTo=(SELECT EmployeeId FROM Employee WHERE Title='General Manager')",
        None,
    ),
    (
        "easy",
        "In how many different countries do the store's customers live?",
        "SELECT COUNT(DISTINCT Country) FROM Customer",
        None,
    ),
    (
        "easy",
        "What is the total of all invoices issued in 2011, rounded to two decimals?",
        "SELECT ROUND(SUM(Total),2) FROM Invoice WHERE strftime('%Y',InvoiceDate)='2011'",
        None,
    ),
    # medium
    (
        "medium",
        "Which artist has the most albums in the store, and how many albums do they have?",
        "SELECT ar.Name, COUNT(*) c FROM Album al JOIN Artist ar USING(ArtistId) GROUP BY ar.ArtistId ORDER BY c DESC LIMIT 1",
        None,
    ),
    (
        "medium",
        "Which genre has the most tracks, and how many tracks is that?",
        "SELECT g.Name, COUNT(*) c FROM Track t JOIN Genre g USING(GenreId) GROUP BY g.GenreId ORDER BY c DESC LIMIT 1",
        None,
    ),
    (
        "medium",
        "Which country's customers spent the most in total, and what was that total, rounded to two decimals?",
        "SELECT BillingCountry, ROUND(SUM(Total),2) s FROM Invoice GROUP BY BillingCountry ORDER BY s DESC LIMIT 1",
        None,
    ),
    (
        "medium",
        "Which customer has spent the most money in total? Give their full name and the total rounded to two decimals.",
        "SELECT c.FirstName||' '||c.LastName, ROUND(SUM(i.Total),2) s FROM Invoice i JOIN Customer c USING(CustomerId) GROUP BY c.CustomerId ORDER BY s DESC LIMIT 1",
        None,
    ),
    (
        "medium",
        "Which sales support agent's customers generated the most invoice revenue? Give the agent's full name and the revenue rounded to two decimals.",
        "SELECT e.FirstName||' '||e.LastName, ROUND(SUM(i.Total),2) s FROM Invoice i JOIN Customer c USING(CustomerId) JOIN Employee e ON e.EmployeeId=c.SupportRepId GROUP BY e.EmployeeId ORDER BY s DESC LIMIT 1",
        None,
    ),
    (
        "medium",
        "How many tracks are in the playlist named 'Grunge'?",
        "SELECT COUNT(*) FROM PlaylistTrack pt JOIN Playlist p USING(PlaylistId) WHERE p.Name='Grunge'",
        None,
    ),
    (
        "medium",
        "What is the average length of a track in the 'Jazz' genre, in whole seconds (rounded down)?",
        "SELECT CAST(AVG(Milliseconds)/1000 AS INT) FROM Track JOIN Genre USING(GenreId) WHERE Genre.Name='Jazz'",
        None,
    ),
    (
        "medium",
        "Which media type has sold the most units (invoice line quantities), and how many units?",
        "SELECT m.Name, SUM(il.Quantity) q FROM InvoiceLine il JOIN Track t USING(TrackId) JOIN MediaType m USING(MediaTypeId) GROUP BY m.MediaTypeId ORDER BY q DESC LIMIT 1",
        None,
    ),
    # hard
    (
        "hard",
        "Which artist earned the most revenue from track sales, and how much, rounded to two decimals?",
        "SELECT ar.Name, ROUND(SUM(il.UnitPrice*il.Quantity),2) s FROM InvoiceLine il JOIN Track t USING(TrackId) JOIN Album al USING(AlbumId) JOIN Artist ar USING(ArtistId) GROUP BY ar.ArtistId ORDER BY s DESC LIMIT 1",
        None,
    ),
    (
        "hard",
        "Which genre brought in the most revenue from customers in the USA, and how much, rounded to two decimals?",
        "SELECT g.Name, ROUND(SUM(il.UnitPrice*il.Quantity),2) s FROM InvoiceLine il JOIN Invoice i USING(InvoiceId) JOIN Track t USING(TrackId) JOIN Genre g USING(GenreId) WHERE i.BillingCountry='USA' GROUP BY g.GenreId ORDER BY s DESC LIMIT 1",
        None,
    ),
    (
        "hard",
        "How many tracks have never been sold?",
        "SELECT COUNT(*) FROM Track WHERE TrackId NOT IN (SELECT TrackId FROM InvoiceLine)",
        None,
    ),
    (
        "hard",
        "How many artists have no albums in the store?",
        "SELECT COUNT(*) FROM Artist WHERE ArtistId NOT IN (SELECT ArtistId FROM Album)",
        None,
    ),
    (
        "hard",
        "In which month of 2012 was revenue highest? Give the month as YYYY-MM and the revenue rounded to two decimals.",
        "SELECT strftime('%Y-%m',InvoiceDate) m, ROUND(SUM(Total),2) s FROM Invoice WHERE strftime('%Y',InvoiceDate)='2012' GROUP BY m ORDER BY s DESC LIMIT 1",
        None,
    ),
    (
        "hard",
        "Which album has the highest number of distinct customers who bought at least one of its tracks? Give the album title and that number of customers.",
        "SELECT al.Title, COUNT(DISTINCT i.CustomerId) c FROM InvoiceLine il JOIN Invoice i USING(InvoiceId) JOIN Track t USING(TrackId) JOIN Album al USING(AlbumId) GROUP BY al.AlbumId ORDER BY c DESC LIMIT 1",
        None,
    ),
    (
        "hard",
        "How many customers have bought tracks from at least 10 different genres?",
        "SELECT COUNT(*) FROM (SELECT i.CustomerId FROM InvoiceLine il JOIN Invoice i USING(InvoiceId) JOIN Track t USING(TrackId) GROUP BY i.CustomerId HAVING COUNT(DISTINCT t.GenreId) >= 10)",
        None,
    ),
    (
        "hard",
        "What share of all invoice revenue came from customers in Germany, France and the United Kingdom combined? Give the percentage rounded to one decimal.",
        "SELECT ROUND(100.0*SUM(CASE WHEN BillingCountry IN ('Germany','France','United Kingdom') THEN Total ELSE 0 END)/SUM(Total),1) FROM Invoice",
        None,
    ),
    (
        "hard",
        "Not counting the General Manager, which employee has the most people reporting to them, directly or through others? Give their full name.",
        "WITH RECURSIVE r(boss, emp) AS (SELECT ReportsTo, EmployeeId FROM Employee WHERE ReportsTo IS NOT NULL UNION ALL SELECT e.ReportsTo, r.emp FROM Employee e JOIN r ON e.EmployeeId=r.boss WHERE e.ReportsTo IS NOT NULL) SELECT e.FirstName||' '||e.LastName FROM r JOIN Employee e ON e.EmployeeId=r.boss WHERE e.Title <> 'General Manager' GROUP BY r.boss ORDER BY COUNT(*) DESC LIMIT 1",
        None,
    ),
    (
        "hard",
        "Which playlist contains the most tracks from the 'Rock' genre, and how many Rock tracks does it contain? Count each track once.",
        "SELECT p.Name, COUNT(DISTINCT t.TrackId) c FROM PlaylistTrack pt JOIN Playlist p USING(PlaylistId) JOIN Track t USING(TrackId) JOIN Genre g USING(GenreId) WHERE g.Name='Rock' GROUP BY p.PlaylistId ORDER BY c DESC LIMIT 1",
        None,
    ),
    # harder, added 2026-10-19 after the first 24 proved near-perfect for both models, written and
    # checked against the database before any agent saw them: NULLs, ties with a stated
    # tie-break, date arithmetic, window functions, "every one of", and nested aggregates.
    (
        "harder",
        "What percentage of tracks have no composer listed? Round to one decimal.",
        "SELECT ROUND(100.0*SUM(Composer IS NULL)/COUNT(*),1) FROM Track",
        None,
    ),
    (
        "harder",
        "How many customers have no company listed and live in a country with at least 5 customers?",
        "SELECT COUNT(*) FROM Customer WHERE Company IS NULL AND Country IN (SELECT Country FROM Customer GROUP BY Country HAVING COUNT(*)>=5)",
        None,
    ),
    (
        "harder",
        "Which employee was the youngest on the day they were hired? Give their full name and their age in whole years on that day.",
        "SELECT FirstName||' '||LastName, CAST((julianday(HireDate)-julianday(BirthDate))/365.25 AS INT) a FROM Employee ORDER BY julianday(HireDate)-julianday(BirthDate) LIMIT 1",
        None,
    ),
    (
        "harder",
        "For the customer with the most invoices, what is the average invoice total, rounded to two decimals? If several customers tie on invoice count, use the one with the lowest CustomerId.",
        "WITH c AS (SELECT CustomerId FROM Invoice GROUP BY CustomerId ORDER BY COUNT(*) DESC, CustomerId LIMIT 1) SELECT ROUND(AVG(Total),2) FROM Invoice WHERE CustomerId=(SELECT CustomerId FROM c)",
        None,
    ),
    (
        "harder",
        "What is the longest gap, in days, between two consecutive invoices of the same customer?",
        "SELECT MAX(g) FROM (SELECT CAST(julianday(InvoiceDate)-julianday(LAG(InvoiceDate) OVER (PARTITION BY CustomerId ORDER BY InvoiceDate)) AS INT) g FROM Invoice)",
        None,
    ),
    (
        "harder",
        "How many albums contain tracks from more than one genre?",
        "SELECT COUNT(*) FROM (SELECT AlbumId FROM Track GROUP BY AlbumId HAVING COUNT(DISTINCT GenreId)>1)",
        None,
    ),
    (
        "harder",
        "Which country had the largest increase in invoice revenue from 2009 to 2013? Give the country and the increase rounded to two decimals.",
        "SELECT BillingCountry, ROUND(SUM(CASE WHEN strftime('%Y',InvoiceDate)='2013' THEN Total ELSE 0 END)-SUM(CASE WHEN strftime('%Y',InvoiceDate)='2009' THEN Total ELSE 0 END),2) d FROM Invoice GROUP BY BillingCountry ORDER BY d DESC LIMIT 1",
        None,
    ),
    (
        "harder",
        "How many customers bought at least one track from every one of the genres Rock, Jazz and Blues?",
        "SELECT COUNT(*) FROM (SELECT i.CustomerId FROM InvoiceLine il JOIN Invoice i USING(InvoiceId) JOIN Track t USING(TrackId) JOIN Genre g USING(GenreId) WHERE g.Name IN ('Rock','Jazz','Blues') GROUP BY i.CustomerId HAVING COUNT(DISTINCT g.Name)=3)",
        None,
    ),
    (
        "harder",
        "Which sales support agent has customers in the most different countries, and how many countries is that?",
        "SELECT e.FirstName||' '||e.LastName, COUNT(DISTINCT c.Country) n FROM Customer c JOIN Employee e ON e.EmployeeId=c.SupportRepId GROUP BY e.EmployeeId ORDER BY n DESC LIMIT 1",
        None,
    ),
    (
        "harder",
        "What share of the store's revenue comes from tracks priced above the most common track price? Give the percentage rounded to one decimal.",
        "SELECT ROUND(100.0*SUM(CASE WHEN il.UnitPrice > (SELECT UnitPrice FROM Track GROUP BY UnitPrice ORDER BY COUNT(*) DESC LIMIT 1) THEN il.UnitPrice*il.Quantity ELSE 0 END)/SUM(il.UnitPrice*il.Quantity),1) FROM InvoiceLine il",
        None,
    ),
    (
        "harder",
        "Among artists with at least 3 albums, which has the highest average number of tracks per album? Give the artist and the average rounded to one decimal.",
        "SELECT ar.Name, ROUND(1.0*COUNT(t.TrackId)/COUNT(DISTINCT al.AlbumId),1) a FROM Artist ar JOIN Album al USING(ArtistId) JOIN Track t USING(AlbumId) GROUP BY ar.ArtistId HAVING COUNT(DISTINCT al.AlbumId)>=3 ORDER BY a DESC LIMIT 1",
        None,
    ),
    (
        "harder",
        "How many invoices contain tracks from more than one media type?",
        "SELECT COUNT(*) FROM (SELECT il.InvoiceId FROM InvoiceLine il JOIN Track t USING(TrackId) GROUP BY il.InvoiceId HAVING COUNT(DISTINCT t.MediaTypeId)>1)",
        None,
    ),
]
