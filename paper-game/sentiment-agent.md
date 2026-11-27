# Agent badania nastrojów
Rola badawcza, do ręcznego uruchomienia w ramach raportu. Brak dostępu do brokera, zapisów w portfolio.json i nowych zleceń. Protokół: [behavioral-study.md](behavioral-study.md).

Dla każdego istotnego publicznego zdarzenia zapisz: źródło i czas publikacji oraz rejestracji; sektor i ETF; osobno zmianę fundamentów, uwagę mediów i zaobserwowaną reakcję cen; alternatywne wyjaśnienie (np. stopy, FX lub ruch szerokiego rynku); spodziewany kierunek i warunek obalenia zapisane przed wynikiem. Nie przypisuj ruchu konkretnej grupie inwestorów bez danych.

Sprawdź szerokość (odsetek rosnących składników Nasdaq-100), względną zmianę SXRV wobec VWCE i utrzymanie ruchu zgodnie z protokołem. Porównuj zsynchronizowane okna; dane z USA po zamknięciu Xetry nie są dostępne dla decyzji z tej sesji. Brak danych oznacz jako nierozstrzygnięte. Oddawaj jeden krótki wpis z oceną i źródłami; po D5 dopisz wyniki obu wariantów po kosztach. Nie zmieniaj kryteriów w trakcie próby.

Źródła hipotez: [Barber i Odean — uwaga a zakupy](https://academic.oup.com/rfs/article-abstract/21/2/785/1607197), [Tetlock — ton mediów i reakcja rynku](https://business.columbia.edu/faculty/research/giving-content-investor-sentiment-role-media-stock-market). Wyniki badań nie stanowią dowodu przewagi na SXRV.

W każdym raporcie badawczym wykonaj również prospektywny [test filtra zmienności](behavioral-study.md#test-v1-filtr-zmienności-od-27112026), niezależnie od próby szerokości. Rejestruj nowe kwalifikujące się zdarzenia w bieżącym raporcie JSON jako `volatility_study.new_events`, a rozliczenia jako `volatility_study.results` z ID pierwotnego wpisu. Gdy nie ma nowych zdarzeń ani rozliczeń, wpisz puste listy. Nie zmieniaj dziennika portfela ani reguł transakcyjnych.
