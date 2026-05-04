import pandas as pd
a = pd.read_parquet('data/automl/dataset_final_tfm.parquet')
b = pd.read_parquet('data/automl/df_exp_automl_D_strict.parquet')
print('Shapes iguales:', a.shape == b.shape)
print('Columnas iguales:', list(a.columns) == list(b.columns))
print('Contenido igual:', a.equals(b))
