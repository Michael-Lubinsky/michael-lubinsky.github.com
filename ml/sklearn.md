### Decision Trees
<https://miptgirl.medium.com/mining-rules-from-data-4fd9f559c608>

### RandomForest

<https://towardsdatascience.com/understanding-random-forest-using-python-scikit-learn/>

Example:
Программа принимает набор данных с несколькими признаками  
и определяет наиболее важные признаки для предсказания целевой переменной с помощью модели RandomForest. 
Программа должна выводить результаты в виде списка признаков, отсортированных по важности.

```python
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

def feature_importance(file):
    data = pd.read_csv(file)
    X = data.drop(columns=['target'])
    y = data['target']
    
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2)
    
    model = RandomForestClassifier()
    model.fit(X_train, y_train)
    
    importance = pd.Series(model.feature_importances_, index=X.columns).sort_values(ascending=False)
    print("Важные признаки:\n", importance)

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Использование: python app.py <файл.csv>")
    else:
        feature_importance(sys.argv[1])
```        
