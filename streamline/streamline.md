### Streamlit

https://www.squadbase.dev/en/ebooks/streamlit-bi-overview

streamlit run myapp.py

https://pybit.es/articles/from-backend-to-frontend-connecting-fastapi-and-streamlit/

https://drlee.io/a-comprehensive-guide-to-streamlit-cloud-building-interactive-and-beautiful-data-apps-af747bbac3e0


### Multi-page support:

https://arshren.medium.com/building-interactive-predictive-machine-learning-workflow-with-streamlit-330188c7ead0

https://medium.com/codefile/streamlit-navigating-multi-page-apps-with-v1-30-0-87146f997f51

```
import streamlit as st

st.header("Multipage navigation")

if st.button("Home page"):
    st.switch_page("multipage-nav1.py")
if st.button("Page 1"):
    st.switch_page("pages/page1.py")
if st.button("Page 2"):
    st.switch_page("pages/page2.py")
```
